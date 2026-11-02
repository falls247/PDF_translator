#!/usr/bin/env python3
"""翻訳HTMLの構造、参照先、収録番号を検査する。"""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
import re
import sys

root = Path(__file__).resolve().parent.parent
page = root / 'outputs/language_models_are_unsupervised_multitask_learners/index.html'
text = page.read_text(encoding='utf-8')
void = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

class Audit(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.ids = set()
        self.links = []
        self.errors = []
        self.counts = Counter()
        self.has_lang = False
        self.has_charset = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.counts[tag] += 1
        if tag == 'html': self.has_lang = attrs.get('lang') == 'ja'
        if tag == 'meta' and attrs.get('charset', '').lower() == 'utf-8': self.has_charset = True
        if tag not in void: self.stack.append(tag)
        if 'id' in attrs:
            if attrs['id'] in self.ids: self.errors.append(f"ID重複: {attrs['id']}")
            self.ids.add(attrs['id'])
        if tag == 'img' and not attrs.get('alt'): self.errors.append('画像に代替テキストがない')
        for attr in ('href', 'src'):
            if attr in attrs: self.links.append(attrs[attr])
    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f'タグの対応不正: </{tag}> (直前: {self.stack[-1:]})')
        else:
            self.stack.pop()

check = Audit()
check.feed(text)
check.close()
if check.stack: check.errors.append(f'閉じていないタグ: {check.stack}')
if not check.has_lang or not check.has_charset: check.errors.append('言語指定または文字コード指定がない')
if '\ufffd' in text: check.errors.append('Unicode置換文字を検出')
for target in check.links:
    if target.startswith('#'):
        if target[1:] not in check.ids: check.errors.append(f'ページ内リンク先なし: {target}')
    elif not re.match(r'^(https?:|mailto:)', target):
        if not (page.parent / unquote(target)).is_file(): check.errors.append(f'ファイルなし: {target}')
for label, count in [('図', 5), ('表', 17)]:
    for number in range(1, count + 1):
        if not re.search(fr'{label}{number}(?!\d)', text): check.errors.append(f'{label}{number} がない')
if check.counts['figure'] != 5 or check.counts['img'] != 5:
    check.errors.append('図または図画像の数が5ではない')
if check.counts['table'] != 6:
    check.errors.append('HTML表の数が6ではない')
print(f"図: {check.counts['figure']}、HTML表: {check.counts['table']}、節: {check.counts['section']}、参照: {len(check.links)}")
print('\n'.join(check.errors) if check.errors else '検証成功')
sys.exit(bool(check.errors))
