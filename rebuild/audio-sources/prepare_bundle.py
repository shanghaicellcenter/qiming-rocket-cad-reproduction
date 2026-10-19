"""Snapshot current approved text without generating speech or taking a writer lock."""
import argparse
import hashlib
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parents[2]
DEFAULT_PROFILE = Path('/Users/qianqiming/Documents/Codex/2026-10-19/ni/work/rocket-v2/breeze-shared-voice-profile.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(source, profile_path):
    original = source.read_bytes()
    narration = json.loads(original)
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    items = [('intro', narration['intro'])] + [('stage' + x['stage_id'], x) for x in narration['stages']] + [('outro', narration['outro'])]
    assert len(items) == 17
    clips = []
    for key, row in items:
        text = row['narration_zh']
        sentences = re.findall(r'[^。！？；]+[。！？；]?', text)
        assert ''.join(sentences) == text
        clips.append({
            'id': key, 'title_zh': row['title_zh'], 'text': text,
            'text_sha256': sha(text.encode()),
            'han_character_count': len(re.findall(r'[\u4e00-\u9fff]', text)),
            'generation_unit': 'whole paragraph, exactly one API request; no sentence concatenation',
            'sentences': [{'id': f'{key}-s{i+1:02d}', 'text': sentence} for i, sentence in enumerate(sentences)],
        })
    bundle = {
        'engine': 'Breeze2', 'project_display_name': '启明火箭',
        'source_narration_sha256': sha(original),
        'source_narration_original_file': str(source.resolve()),
        'source_han_count': sum(x['han_character_count'] for x in clips),
        'source_reported_han_count': narration.get('total_han_character_count'),
        'profile_id': profile['profileId'], 'reference_sha256': profile['referenceSha256'],
        'voice_policy': 'fixed native reference; no pitch shift, speed alteration, effects, cloud, fallback engine, or sentence-by-sentence synthesis',
        'sentence_policy': 'sentence metadata is for independent post-generation acoustic alignment only',
        'status': 'prepared_not_submitted_waiting_for_root_pilot_release',
        'eligible_for_final_movie': False, 'clips': clips,
    }
    BASE.mkdir(exist_ok=True)
    (BASE / 'source-narration.snapshot.json').write_bytes(original)
    (BASE / 'profile.snapshot.json').write_bytes(profile_bytes)
    (BASE / 'clips.json').write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\n')
    target = BASE / 'texts'; target.mkdir(exist_ok=True)
    for row in clips:
        (target / (row['id'] + '.txt')).write_text(row['text'] + '\n')
    print(json.dumps({key: bundle[key] for key in ['engine', 'source_narration_sha256', 'source_han_count', 'source_reported_han_count', 'status']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=WORKSPACE / 'work/virtual-assembly/narration-draft.json')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    args = parser.parse_args()
    prepare(args.source, args.profile)
