"""Prepared offline CPU Whisper review. No TTS, no text prompt, no automatic approval."""
import argparse
import difflib
import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODEL = Path('/home/qianqiming/.cache/huggingface/hub/models--openai--whisper-large-v3-turbo/snapshots/41f01f3fe87f28c78e2fbf8b568835947dd65ed9')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def normalized(text):
    return ''.join(c.lower() for c in text if c.isalnum())


def align_sentences(clip, asr):
    targets = clip['sentences']
    expected = ''.join(normalized(x['text']) for x in targets)
    recognized, word_for_char = '', []
    for i, word in enumerate(asr['words']):
        chars = normalized(word['text'])
        recognized += chars; word_for_char.extend([i] * len(chars))
    source_to_recognized = {}
    for block in difflib.SequenceMatcher(a=expected, b=recognized, autojunk=False).get_matching_blocks():
        for offset in range(block.size):
            source_to_recognized[block.a + offset] = block.b + offset
    cursor, rows = 0, []
    for sentence in targets:
        length = len(normalized(sentence['text']))
        mapped = [source_to_recognized[n] for n in range(cursor, cursor + length) if n in source_to_recognized]
        word_ids = sorted({word_for_char[n] for n in mapped})
        words = [asr['words'][n] for n in word_ids]
        valid = bool(words) and all(type(w.get('start')) in (int,float) and type(w.get('end')) in (int,float) and math.isfinite(w['start']) and math.isfinite(w['end']) for w in words)
        rows.append({
            'sentence_id': sentence['id'], 'target_text': sentence['text'],
            'start': min(w['start'] for w in words) if valid else None,
            'end': max(w['end'] for w in words) if valid else None,
            'recognized_span': ''.join(w['text'] for w in words),
            'whisper_word_indices': word_ids,
            'matched_normalized_characters': len(mapped), 'target_normalized_characters': length,
            'exact_character_coverage': len(mapped) / length if length else 0,
            'timing_basis': 'Observed Whisper decoder word spans matched to target text; no duration averaging',
            'human_content_passed': False,
        })
        cursor += length
    overlaps = [rows[i]['sentence_id'] for i in range(1,len(rows)) if rows[i]['start'] is not None and rows[i-1]['end'] is not None and rows[i]['start'] < rows[i-1]['end']]
    return {'engine':'Breeze2', 'asr_engine':asr['engine'], 'input_wav_sha256':asr['input_wav_sha256'], 'text_sha256':clip['text_sha256'], 'asr_is_independent_of_expected_text':True, 'acoustic_timestamps_are_approximate':True, 'sentences':rows, 'overlapping_sentence_spans':overlaps, 'recognized_text':asr['transcript'], 'exact_whole_text_match_after_punctuation_normalization':expected == recognized, 'eligible_for_final_movie':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=BASE)
    parser.add_argument('--run', action='store_true', help='Only after actual WAV generation and explicit Root scheduling')
    parser.add_argument('--device', choices=['cpu','cuda'], default='cpu')
    parser.add_argument('--only', help='One existing clip ID for an isolated device probe')
    parser.add_argument('--output-root', type=Path, help='Isolated probe output; never touches canonical per-clip files')
    args = parser.parse_args(); base = args.base.resolve()
    bundle = json.loads((base/'clips.json').read_text())
    if not args.run:
        print(json.dumps({'prepared_only':True,'model_path_exists':MODEL.is_dir(),'paragraphs':len(bundle['clips']),'asr_started':False,'tts_submitted':False})); return
    status = json.loads((base/'results/status.json').read_text())
    assert status['engine'] == 'Breeze2' and status['source_narration_sha256'] == bundle['source_narration_sha256']
    generated = {r['id']:r for r in status['clips'] if r['status']=='generated_candidate'}
    assert set(generated) == set(status['selected_clip_ids']) == {'stage10','stage12'}, 'Only the two approved revision candidates' 
    process_path = (args.output_root / 'asr-process.json') if args.output_root else base/'results/asr-process.json'
    process_path.parent.mkdir(parents=True,exist_ok=True)
    write(process_path, {'pid':os.getpid(),'status':'starting_offline_model','device':args.device,'engine':'Whisper large-v3-turbo','model':str(MODEL),'shared_writer_lock_acquired':False,'tts_requests':0})
    print('ASR_STARTED',args.device,os.getpid(),flush=True)
    # The same existing CPU Whisper path as the independently inspected source runner.
    settings={'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','OMP_NUM_THREADS':'6','MKL_NUM_THREADS':'6','TOKENIZERS_PARALLELISM':'false'}
    if args.device=='cpu':settings['CUDA_VISIBLE_DEVICES']=''
    for key,value in settings.items():
        os.environ[key] = value
    import numpy as np
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline
    # This process already supplies ffmpeg-decoded numpy at16kHz. Transformers5
    # otherwise imports an unrelated CUDA12 TorchCodec decoder to type-check it.
    # Disable that optional decoder check in THIS process only; no package edits.
    from transformers.pipelines import automatic_speech_recognition as asr_module
    asr_module.is_torchcodec_available = lambda: False
    torch.set_num_threads(6); torch.set_num_interop_threads(1)
    processor = WhisperProcessor.from_pretrained(str(MODEL), local_files_only=True)
    dtype = torch.float16 if args.device=='cuda' else torch.float32
    if args.device=='cuda':assert torch.cuda.is_available(), 'CUDA unavailable; keep existing CPU runner'
    model = WhisperForConditionalGeneration.from_pretrained(str(MODEL), local_files_only=True, dtype=dtype, attn_implementation='eager').to(args.device).eval()
    recognizer = pipeline('automatic-speech-recognition', model=model, tokenizer=processor.tokenizer, feature_extractor=processor.feature_extractor, device=0 if args.device=='cuda' else 'cpu')
    for clip in bundle['clips']:
        if clip['id'] not in generated:continue
        if args.only and clip['id'] != args.only:continue
        row = generated[clip['id']]; wav = base/row['wav_file']; assert sha(wav)==row['wav_sha256']
        target = (args.output_root/(clip['id']+'.asr.json')) if args.output_root else wav.with_suffix('.asr.json')
        alignment = (args.output_root/(clip['id']+'.sentence-alignment.json')) if args.output_root else wav.with_suffix('.sentence-alignment.json')
        if target.exists():
            result = json.loads(target.read_text()); assert result['input_wav_sha256']==row['wav_sha256']
        else:
            start = time.monotonic()
            raw = subprocess.run(['/usr/bin/ffmpeg','-nostdin','-v','error','-i',str(wav),'-f','f32le','-ac','1','-ar','16000','pipe:1'],capture_output=True,check=True).stdout
            samples = np.frombuffer(raw,dtype='<f4').copy()
            # Expected narration is deliberately NOT supplied as a prompt to recognition.
            decoded = recognizer({'raw':samples,'sampling_rate':16000},return_timestamps='word',generate_kwargs={'language':'zh','task':'transcribe','max_new_tokens':192,'do_sample':False})
            result = {'engine':'Whisper large-v3-turbo','device':args.device,'dtype':str(dtype),'gpu_name':torch.cuda.get_device_name(0) if args.device=='cuda' else None,'offline':True,'input_wav_sha256':row['wav_sha256'],'duration_seconds':len(samples)/16000,'transcript':decoded['text'],'words':[{'start':c['timestamp'][0],'end':c['timestamp'][1],'text':c['text']} for c in decoded.get('chunks',[])],'elapsed_seconds':time.monotonic()-start,'target_text_supplied_to_asr':False,'timestamps':'Approximate decoder acoustic word alignment; no character-duration averaging'}
            write(target,result)
        write(alignment,align_sentences(clip,result))
        write(process_path, {'pid':os.getpid(),'status':'transcribing','device':args.device,'last_completed':clip['id'],'engine':'Whisper large-v3-turbo','shared_writer_lock_acquired':False,'tts_requests':0})
        print('ASR_REVIEW_CANDIDATE',clip['id'],flush=True)
    write(process_path, {'pid':os.getpid(),'status':'complete_requested_set','device':args.device,'only':args.only,'engine':'Whisper large-v3-turbo','shared_writer_lock_acquired':False,'tts_requests':0})


if __name__ == '__main__':
    main()
