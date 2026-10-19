"""Publish only source-bound, independently transcribed, sample-preserving Breeze tracks."""
from pathlib import Path
import datetime, hashlib, json, math, shutil, wave

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
REV = BASE / 'revision-53db8ccf997e'
SOURCE = ROOT / 'work/virtual-assembly/narration-draft.json'
CANONICAL = SOURCE.with_name('narration-audio-manifest.json')
CURRENT_SHA = '53db8ccf997ed44bfcac4b214841c985d3761ec323058a1d80ce7d33712620d2'
OLD_SHA = '96c7b3e545973bd573445474d9bc1f380b778c6871609509e0bed5bb6693b7e7'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def norm(text):
    return ''.join(c.lower() for c in text if c.isalnum())

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)

# Every alternative below was read in the independent full-text review. These
# preserve Mandarin pronunciation in this context. Different-tone ambiguities
# are NOT added here: they require the independent second recognizer instead.
HOMOPHONES = {
    ('筒', '桶'), ('筒', '统'), ('贮', '住'), ('贮', '炷'), ('贮', '柱'),
    ('室', '式'), ('只', '支'), ('件', '键'), ('芯', '心'), ('剂', '技'),
    ('箭', '舰'), ('箭', '键'), ('翼', '意'), ('隔', '格'), ('舱', '仓'),
    ('壁', '臂'), ('源', '原'), ('源', '元'), ('源', '圆'), ('原', '元'),
    ('原', '圆'), ('锥', '椎'), ('树', '术'), ('另', '令'), ('核', '和'),
    ('它', '他'),
}

def review_equivalence(target, transcript):
    expected, observed = norm(target), norm(transcript)
    assert len(expected) == len(observed), ('ASR insertion/deletion', target, transcript)
    differences = []
    for i, (a, b) in enumerate(zip(expected, observed)):
        if a != b:
            assert (a, b) in HOMOPHONES, ('Unresolved pronunciation/text difference', i, a, b, target, transcript)
            differences.append({'index': i, 'target': a, 'recognized': b, 'classification': 'documented same-pronunciation character choice'})
    return differences

def verify_audio(track):
    raw, final = Path(track['raw_wav_path']), Path(track['wav_path'])
    assert sha(raw) == track['raw_wav_sha256'] and sha(final) == track['wav_sha256']
    frames = []
    for p in [raw, final]:
        with wave.open(str(p), 'rb') as wav:
            assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (24000, 1, 2)
            frames.append(wav.getnframes())
            pcm = wav.readframes(wav.getnframes())
            assert len(pcm) == frames[-1] * 2
    assert frames[0] == frames[1] == track['frames'] == track['raw_frames']
    assert abs(track['duration_seconds'] - frames[0] / 24000) < 1e-12
    assert track['full_scale_samples'] == 0 and track['frame_count_unchanged']
    assert track['source_digital_zeros_remain_zero']
    assert hashlib.sha256(pcm).hexdigest() == track['pcm_sha256']

def main():
    assert sha(SOURCE) == CURRENT_SHA
    old = json.loads((BASE / 'leveling-audit.json').read_text())
    new = json.loads((REV / 'leveling-audit.json').read_text())
    bundle = json.loads((REV / 'clips.json').read_text())
    assert old['source_narration_sha256'] == OLD_SHA
    assert new['source_narration_sha256'] == bundle['source_narration_sha256'] == CURRENT_SHA
    assert old['all17_processed'] and new['all_requested_processed']
    old_tracks = {r['id']: r for r in old['tracks']}
    revised_tracks = {r['id']: r for r in new['tracks']}
    assert set(revised_tracks) == {'stage10', 'stage12'}
    old_para_path = BASE / 'raw-archive/results/paraformer-crosscheck.json'
    new_para_path = REV / 'raw-archive/results/paraformer-crosscheck.json'
    old_para = {r['id']: r for r in json.loads(old_para_path.read_text())}
    new_para = {r['id']: r for r in json.loads(new_para_path.read_text())}
    assert set(new_para) == {'stage10', 'stage12'}
    review_rows, tracks = [], []
    prior_review_path = BASE / 'asr-text-review/progress/text-review.json'
    prior_review = {r['id']: r for r in json.loads(prior_review_path.read_text())['clips']}
    fields = ['id','text','text_sha256','engine','raw_wav_path','raw_wav_sha256','wav_path','wav_sha256','pcm_sha256','duration_seconds','sample_rate','channels','sample_width','frames','raw_frames','frame_count_unchanged','source_digital_zeros_remain_zero','full_scale_samples','requested_constant_gain_db','applied_constant_gain_db','gain_limited_by_true_peak','target_voiced_median_dbfs','final_loudness','asr_json_path','asr_json_sha256','asr_device','asr_dtype','asr_words','subtitle_sentences']
    for clip in bundle['clips']:
        ident = clip['id']; revised = ident in revised_tracks
        detailed = revised_tracks[ident] if revised else old_tracks[ident]
        assert detailed['text_sha256'] == clip['text_sha256'] == hashlib.sha256(clip['text'].encode()).hexdigest()
        verify_audio(detailed)
        asr_path = Path(detailed['asr_json_path']); asr = json.loads(asr_path.read_text())
        assert sha(asr_path) == detailed['asr_json_sha256']
        assert asr['input_wav_sha256'] == detailed['raw_wav_sha256']
        assert asr['target_text_supplied_to_asr'] is False
        assert asr['words'] == detailed['asr_words'] and asr['words']
        if not revised:
            earlier = prior_review[ident]
            assert earlier['full_text_reviewed'] and not earlier['integrity_issues'] and not earlier['word_timestamp_issues'] and not earlier['sentence_boundary_issues']
        secondary = (new_para if revised else old_para).get(ident)
        if secondary:
            assert secondary['input_wav_sha256'] == detailed['raw_wav_sha256']
            assert secondary['expected_text_supplied'] is False and secondary['hotword_supplied'] is False
            compared = secondary['transcript']
            comparison_basis = 'Full independent CPU Paraformer transcript; original Whisper transcript retained unchanged'
        else:
            compared = asr['transcript']
            comparison_basis = 'Full independent Whisper transcript'
        differences = review_equivalence(clip['text'], compared)
        last = 0.0
        for word in detailed['asr_words']:
            a, b = word['start'], word['end']
            assert isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isfinite(a) and math.isfinite(b)
            assert 0 <= a <= b <= detailed['duration_seconds'] + .001 and a >= last - 1e-6
            last = b
        last = 0.0
        for sentence in detailed['subtitle_sentences']:
            a, b = sentence['start'], sentence['end']
            assert 0 <= a < b <= detailed['duration_seconds'] + .001 and a >= last - 1e-6
            last = b
        assert norm(''.join(s['target_text'] for s in detailed['subtitle_sentences'])) == norm(clip['text'])
        track = {k:detailed[k] for k in fields}
        track.update(source_narration_sha256=CURRENT_SHA,
                     generation_source_narration_sha256=CURRENT_SHA if revised else OLD_SHA,
                     generation_unit='One complete paragraph request; no sentence stitching',
                     reference_sha256=bundle['reference_sha256'], cfg_scale=1.0, seed=42,
                     instruction_form_field_sent=False,
                     content_review_status='Independent whole-text ASR checked; documented same-pronunciation glyph choices accepted; no unresolved pronunciation ambiguity',
                     independent_asr_content_review_passed=True,
                     human_listened_to_this_track=False,
                     eligible_for_final_movie=True,
                     detailed_leveling_audit_path=str(REV/'leveling-audit.json' if revised else BASE/'leveling-audit.json'),
                     asr_transcript=asr['transcript'],
                     after_voiced_window_median_dbfs=detailed['after']['voiced_window_rms_median_dbfs'])
        metadata_path = Path(track['raw_wav_path']).with_suffix('.request-result.json')
        metadata = json.loads(metadata_path.read_text())
        assert metadata['text_sha256'] == clip['text_sha256'] and metadata['reference_sha256'] == bundle['reference_sha256']
        assert metadata['instruction_form_field_sent'] is False and metadata['request_count'] == 1
        pcm_path = Path(track['raw_wav_path']).with_suffix('.pcm')
        assert sha(pcm_path) == metadata['pcm_sha256']
        track.update(raw_pcm_path=str(pcm_path), raw_pcm_sha256=metadata['pcm_sha256'], generation_request_metadata_path=str(metadata_path))
        if secondary:
            track.update(second_asr_json_path=str(new_para_path if revised else old_para_path), second_asr_record_id=ident)
        review_rows.append({'id':ident,'text_sha256':clip['text_sha256'],'raw_wav_sha256':track['raw_wav_sha256'],'revised_whole_paragraph':revised,'comparison_basis':comparison_basis,'compared_transcript':compared,'documented_homophone_differences':differences,'no_insertions_deletions_or_unresolved_differences':True,'source_bound_actual_word_chunks':len(asr['words']),'acoustic_caption_spans':len(track['subtitle_sentences']),'passed':True})
        tracks.append(track)
    expected = ['intro'] + [f'stage{i:02d}' for i in range(1,16)] + ['outro']
    assert [r['id'] for r in tracks] == expected
    assert sum(r['revised_whole_paragraph'] for r in review_rows) == 2
    report = {'engine':'Breeze2','source_narration_sha256':CURRENT_SHA,'track_count':17,'all_actual_text_and_hash_bindings_passed':True,'all_sample_counts_preserved':True,'actual_word_chunks':sum(len(t['asr_words']) for t in tracks),'actual_caption_spans':sum(len(t['subtitle_sentences']) for t in tracks),'unresolved_pronunciation_differences':[],'human_full_set_listening_performed':False,'voice_naturalness_scope':'Human approved the shared pilot direction; no claim that human listened to all17 generated tracks. ASR content checks do not establish naturalness.','tracks':review_rows}
    review_path = BASE / 'asr-text-review/final17-content-review.json'
    write(review_path, report)
    manifest = {'schema_version':2,'engine':'Breeze2','project_display_name':'启明火箭','status':'all17_actual_ASR_content_and_sample_preserving_leveling_complete','published_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_narration_sha256':CURRENT_SHA,'reference_sha256':bundle['reference_sha256'],'track_count':17,'stage_count':15,'source_han_character_count':bundle['source_han_count'],'source_reported_han_character_count':bundle['source_reported_han_count'],'global_source_revision_policy':'Two changed paragraphs regenerated;15 unchanged per-text SHA256 matches verified and retained. Each generation source SHA recorded separately.','formal_text_approved_by_parent':True,'human_approved_voice_direction':True,'human_listened_to_all17_tracks':False,'speed_or_pitch_modified':False,'sample_rate':24000,'channels':1,'sample_width':2,'compression_filter':old['compressor_filter'],'target_voiced_window_median_dbfs':old['target_voiced_window_median_dbfs'],'no_second_loudnorm':True,'timing_policy':'Original independent Whisper acoustic word spans retained verbatim; target sentence spans map to those actual spans. No character-duration averaging. Soft compression/static gain preserve all sample counts and natural pauses.','total_actual_audio_duration_seconds':sum(t['duration_seconds'] for t in tracks),'generated_candidate_count_including_superseded_two':19,'selected_actual_track_count':17,'asr_checked_track_count':17,'full_text_content_review':str(review_path),'license_evidence':str(BASE/'license-evidence/license-evidence.json'),'usage':'Research/non-commercial digital project visualization; self-hosted Breeze model/output restrictions recorded from existing official repository README.','firered_mixed_into_final_audio':False,'drama3_mixed_into_final_audio':False,'superseded_old_stage10_stage12_eligible':False,'eligible_for_final_movie':True,'tracks':tracks}
    history = BASE/'history';history.mkdir(exist_ok=True)
    if CANONICAL.exists():
        oldcanonical = json.loads(CANONICAL.read_text())
        if oldcanonical.get('engine') != 'Breeze2':
            archive = history/'narration-audio-manifest.rejected-pre-Breeze.json'
            if not archive.exists():shutil.copy2(CANONICAL,archive)
    write(CANONICAL, manifest)
    print(json.dumps({k:manifest[k] for k in ['engine','source_narration_sha256','track_count','total_actual_audio_duration_seconds','eligible_for_final_movie']},ensure_ascii=False))
    print('CONTENT_REVIEW', review_path)

if __name__ == '__main__':
    main()
