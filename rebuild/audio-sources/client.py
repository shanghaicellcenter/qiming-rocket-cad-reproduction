"""Single-writer Breeze2 paragraph client. Default path NEVER submits speech."""
import argparse
import fcntl
import hashlib
import json
import os
import sys
import time
import datetime
import socket
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path

BASE = Path(__file__).resolve().parent
PINNED_API_SOURCE = Path('/home/qianqiming/work/breeze-tts/breeze_infer/api.py')
PINNED_API_SHA = '9cb2d4f377015312ec7264d258d30e452e7f5ed6064919079e5aa278408c203e'
PINNED_REF_SHA = 'b877cfd2a4b951b77e07743a4e569ecca2f3a62e4d990b0b4f2baaaffcd0191f'
EXPECTED_IDS = ['intro'] + [f'stage{i:02d}' for i in range(1, 16)] + ['outro']


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def multipart(clip, profile):
    # These are the actual multipart names read from the running OpenAPI and API source.
    fields = {'text': clip['text'], 'ref_text': profile['referenceText'], 'cfg_scale': '1.0', 'seed': '42'}
    assert set(fields) == {'text', 'ref_text', 'cfg_scale', 'seed'}
    boundary = 'codex-breeze-' + uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="ref_audio"; filename="reference.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode())
    body.extend(Path(profile['referenceAudio']).read_bytes())
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    # No instruction form part, including no empty instruction part.
    return bytes(body), boundary


def wave_info(path):
    with wave.open(str(path), 'rb') as wav:
        result = {'sample_rate': wav.getframerate(), 'channels': wav.getnchannels(), 'sample_width': wav.getsampwidth(), 'frames': wav.getnframes()}
        audio = wav.readframes(result['frames'])
    assert result['sample_rate'] == 24000 and result['channels'] == 1 and result['sample_width'] == 2
    assert result['frames'] > 0 and len(audio) == result['frames'] * 2
    result['duration_seconds'] = result['frames'] / 24000
    result['pcm_sha256'] = sha_bytes(audio)
    return result


def preflight(base, offline=False, health=False):
    bundle = json.loads((base / 'clips.json').read_text())
    profile = json.loads((base / 'profile.snapshot.json').read_text())
    assert bundle['engine'] == 'Breeze2'
    assert [x['id'] for x in bundle['clips']] == EXPECTED_IDS
    assert sha_file(base / 'source-narration.snapshot.json') == bundle['source_narration_sha256']
    assert profile['apiUrl'] == 'http://127.0.0.1:7862/v1/audio/speech'
    assert profile['referenceSha256'] == bundle['reference_sha256'] == PINNED_REF_SHA
    assert profile['cfgScale'] == 1.0 and profile['seed'] == 42
    for clip in bundle['clips']:
        assert sha_bytes(clip['text'].encode()) == clip['text_sha256']
        assert ''.join(s['text'] for s in clip['sentences']) == clip['text']
    report = {'engine': 'Breeze2', 'paragraphs': len(bundle['clips']), 'source_narration_sha256': bundle['source_narration_sha256'], 'source_han_count': bundle['source_han_count'], 'offline': offline, 'speech_requests_sent': 0, 'shared_writer_lock_acquired': False}
    if not offline:
        ref = Path(profile['referenceAudio'])
        assert sha_file(ref) == PINNED_REF_SHA
        report['reference'] = wave_info(ref)
        assert sha_file(PINNED_API_SOURCE) == PINNED_API_SHA, 'API source changed; inspect before dispatch'
        lock = Path(profile['sharedWriterLock']); assert lock.is_file(), 'Existing shared writer file must not be recreated'
        report['shared_lock_file_exists'] = True
    if health:
        assert not offline
        with urllib.request.urlopen('http://127.0.0.1:7862/health', timeout=10) as response:
            report['health'] = json.load(response)
        assert report['health'] == {'status': 'ok', 'sample_rate': 24000}
    return bundle, profile, report


def run_one(base, clip, profile):
    folder = base / 'results' / clip['id']; folder.mkdir(parents=True, exist_ok=True)
    wav_path = folder / (clip['id'] + '.wav')
    raw = folder / (clip['id'] + '.pcm')
    meta = folder / (clip['id'] + '.request-result.json')
    if wav_path.exists() or meta.exists():
        assert wav_path.is_file() and meta.is_file(), 'Partial prior attempt; inspect rather than overwrite'
        previous = json.loads(meta.read_text())
        assert previous['engine'] == 'Breeze2' and previous['text_sha256'] == clip['text_sha256'] and previous['reference_sha256'] == PINNED_REF_SHA
        assert previous['wav_sha256'] == sha_file(wav_path)
        assert previous['pcm_sha256'] == wave_info(wav_path)['pcm_sha256']
        return previous
    body, boundary = multipart(clip, profile)
    request = urllib.request.Request(profile['apiUrl'], data=body, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary, 'Accept': 'audio/pcm'}, method='POST')
    started = time.monotonic(); temporary = raw.with_suffix('.pcm.part')
    assert not temporary.exists() and not raw.exists(), 'Partial prior PCM must be inspected, not overwritten'
    with urllib.request.urlopen(request, timeout=900) as response:
        headers = dict(response.headers)
        rate = response.headers.get('X-Sample-Rate')
        form = response.headers.get('X-Sample-Format')
        assert response.status == 200 and response.headers.get_content_type() == 'audio/pcm'
        assert rate == '24000' and form == 's16le', f'Unexpected native format: {rate}/{form}'
        with temporary.open('xb') as output:
            while True:
                data = response.read(65536)
                if not data:
                    break
                output.write(data)
    payload = temporary.read_bytes()
    assert payload and len(payload) % 2 == 0, 'Empty or truncated PCM'
    temporary.replace(raw)
    wav_tmp = wav_path.with_suffix('.wav.part')
    with wave.open(str(wav_tmp), 'wb') as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(24000); output.writeframes(payload)
    wav_tmp.replace(wav_path)
    row = {**clip, 'engine': 'Breeze2', 'status': 'generated_candidate', 'wav_file': str(wav_path.relative_to(base)), 'raw_pcm_file': str(raw.relative_to(base)), 'wav_sha256': sha_file(wav_path), 'reference_sha256': PINNED_REF_SHA, 'profile_id': profile['profileId'], 'cfg_scale': 1.0, 'seed': 42, 'instruction_form_field_sent': False, 'request_count': 1, 'response_headers': headers, 'elapsed_seconds': time.monotonic() - started, 'post_processing': 'raw PCM wrapped into WAV; no DSP, pitch or speed alteration', 'asr_file': None, 'human_content_passed': False, 'eligible_for_final_movie': False, **wave_info(wav_path)}
    write_json(meta, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=BASE)
    parser.add_argument('--offline', action='store_true', help='Local text/profile preflight only, without Spark file or service access')
    parser.add_argument('--health', action='store_true', help='Read-only GET health, never POST')
    parser.add_argument('--submit', action='store_true', help='Requires a later Root dispatch note and nonblocking shared lock')
    parser.add_argument('--dispatch-note', type=Path)
    args = parser.parse_args(); base = args.base.resolve()
    bundle, profile, check = preflight(base, args.offline, args.health)
    print(json.dumps(check, ensure_ascii=False), flush=True)
    if not args.submit:
        return
    assert not args.offline and args.dispatch_note, 'Explicit Root release note required; currently preparation only'
    note = json.loads(args.dispatch_note.read_text())
    assert note.get('dispatch_allowed') is True and note.get('pilot_passed') is True and note.get('shared_writer_release_confirmed') is True
    assert note.get('source_narration_sha256') == bundle['source_narration_sha256'], 'Dispatch text hash is stale'
    assert note.get('reference_sha256') == PINNED_REF_SHA
    result = {'engine': 'Breeze2', 'project_display_name': '启明火箭', 'source_narration_sha256': bundle['source_narration_sha256'], 'reference_sha256': PINNED_REF_SHA, 'dispatch_note_sha256': sha_file(args.dispatch_note), 'generation_unit': 'one whole-paragraph request per clip, sequential', 'status': 'acquiring_existing_shared_lock', 'eligible_for_final_movie': False, 'clips': []}
    # Existing file is opened read-only: never truncate, replace, delete, or steal a writer lock.
    with Path(profile['sharedWriterLock']).open('rb') as shared:
        try:
            fcntl.flock(shared.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Shared writer busy; stopped without waiting or submitting')
        try:
            acquired = {'pid': os.getpid(), 'hostname': socket.gethostname(), 'lock_file': profile['sharedWriterLock'], 'lock_inode': os.fstat(shared.fileno()).st_ino, 'lock_device': os.fstat(shared.fileno()).st_dev, 'acquired_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'mechanism': 'fcntl.flock LOCK_EX | LOCK_NB succeeded on existing read-only-open shared file', 'source_narration_sha256': bundle['source_narration_sha256'], 'reference_sha256': PINNED_REF_SHA}
            write_json(base / 'results/writer-lock-acquired.json', acquired)
            result['writer'] = acquired
            print('WRITER_LOCK_ACQUIRED', json.dumps(acquired), flush=True)
            result['status'] = 'generating_candidate_serially'; write_json(base / 'results/status.json', result)
            for clip in bundle['clips']:
                result['clips'].append(run_one(base, clip, profile))
                write_json(base / 'results/status.json', result)
                print('GENERATED_CANDIDATE', clip['id'], flush=True)
            result['status'] = 'all17_generated_candidates_pending_independent_ASR_and_listening'
            write_json(base / 'results/status.json', result)
        except Exception as error:
            result['status'] = 'stopped_on_error_no_retry_no_fallback'; result['error'] = str(error)
            write_json(base / 'results/status.json', result)
            raise
        finally:
            fcntl.flock(shared.fileno(), fcntl.LOCK_UN)
            released = {'pid': os.getpid(), 'released_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'mechanism': 'fcntl.flock LOCK_UN called; existing shared file retained and unmodified', 'lock_file': profile['sharedWriterLock']}
            write_json(base / 'results/writer-lock-released.json', released)
            print('WRITER_LOCK_RELEASED', json.dumps(released), flush=True)


if __name__ == '__main__':
    main()
