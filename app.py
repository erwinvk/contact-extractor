#!/usr/bin/env python3
from flask import Flask, request, jsonify
import anthropic
import os
import json
import re

app = Flask(__name__)

HTML = r"""
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Extractor</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f7;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem 1rem;
            color: #1d1d1f;
        }
        h1 { font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem; }

        .api-key-section {
            width: 100%;
            max-width: 480px;
            margin-bottom: 1.5rem;
        }
        .api-key-section label {
            display: block;
            font-size: 0.85rem;
            color: #6e6e73;
            margin-bottom: 0.4rem;
        }
        .api-key-section input {
            width: 100%;
            padding: 0.6rem 0.8rem;
            border: 1.5px solid #d2d2d7;
            border-radius: 10px;
            font-size: 0.9rem;
            outline: none;
            background: white;
        }
        .api-key-section input:focus { border-color: #0071e3; }

        .paste-zone {
            width: 100%;
            max-width: 480px;
            min-height: 160px;
            border: 2px dashed #c7c7cc;
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            background: white;
            cursor: pointer;
            transition: border-color 0.2s, background 0.2s;
            padding: 2rem;
            text-align: center;
        }
        .paste-zone:focus { outline: none; border-color: #0071e3; }
        .paste-zone.active { border-color: #0071e3; background: #f0f6ff; }
        .paste-zone .icon { font-size: 2.5rem; }
        .paste-zone .hint { font-size: 0.9rem; color: #6e6e73; line-height: 1.5; }
        .paste-zone .hint strong { color: #1d1d1f; }

        #preview {
            width: 100%;
            max-width: 480px;
            border-radius: 12px;
            margin-top: 1rem;
            display: none;
            max-height: 280px;
            object-fit: contain;
            background: white;
        }

        .loading {
            display: none;
            margin-top: 1.5rem;
            color: #6e6e73;
            font-size: 0.9rem;
            align-items: center;
            gap: 0.5rem;
        }
        .spinner {
            width: 20px; height: 20px;
            border: 2px solid #d2d2d7;
            border-top-color: #0071e3;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .result-card {
            display: none;
            width: 100%;
            max-width: 480px;
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            margin-top: 1.5rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }

        .gender-toggle {
            display: flex;
            background: #f5f5f7;
            border-radius: 8px;
            padding: 3px;
            margin-bottom: 1rem;
            width: fit-content;
        }
        .gender-toggle button {
            padding: 0.4rem 1rem;
            border: none;
            background: transparent;
            border-radius: 6px;
            font-size: 0.9rem;
            cursor: pointer;
            color: #6e6e73;
            transition: all 0.15s;
        }
        .gender-toggle button.active {
            background: white;
            color: #1d1d1f;
            box-shadow: 0 1px 4px rgba(0,0,0,0.12);
            font-weight: 500;
        }

        .contact-block {
            font-size: 1rem;
            line-height: 1.9;
            color: #1d1d1f;
            background: #f5f5f7;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            font-family: monospace;
            white-space: pre;
        }

        .actions { display: flex; gap: 0.75rem; }
        .btn {
            flex: 1;
            padding: 0.8rem;
            border: none;
            border-radius: 12px;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: opacity 0.15s;
            text-decoration: none;
            text-align: center;
            display: block;
        }
        .btn:active { opacity: 0.7; }
        .btn-copy { background: #0071e3; color: white; }
        .btn-copy.copied { background: #34c759; }
        .btn-call { background: #34c759; color: white; }

        .error {
            display: none;
            margin-top: 1rem;
            color: #ff3b30;
            font-size: 0.9rem;
            text-align: center;
            max-width: 480px;
        }
    </style>
</head>
<body>
    <h1>Contact Extractor</h1>

    <div class="api-key-section">
        <label>Anthropic API Key</label>
        <input type="password" id="apiKey" placeholder="sk-ant-..." autocomplete="off">
    </div>

    <div class="paste-zone" id="pasteZone" tabindex="0">
        <div class="icon">📋</div>
        <div class="hint">
            <strong>Plak een afbeelding hier</strong><br>
            Kopieer de foto in WhatsApp, dan <strong>Cmd+V</strong>
        </div>
    </div>

    <img id="preview" alt="Preview">

    <div class="loading" id="loading">
        <div class="spinner"></div>
        Gegevens worden uitgelezen...
    </div>

    <div class="error" id="error"></div>

    <div class="result-card" id="resultCard">
        <div class="gender-toggle">
            <button id="btnMevrouw" class="active" onclick="setGender('Mevrouw')">Mevrouw</button>
            <button id="btnDhr" onclick="setGender('De heer')">De heer</button>
        </div>
        <div class="contact-block" id="contactBlock"></div>
        <div class="actions">
            <button class="btn btn-copy" id="copyBtn" onclick="copyBlock()">Kopieer</button>
            <a class="btn btn-call" id="callBtn" href="#">Bel</a>
        </div>
    </div>

    <script>
        let currentData = {};
        let currentGender = 'Mevrouw';

        // Load saved API key
        const apiKeyInput = document.getElementById('apiKey');
        apiKeyInput.value = localStorage.getItem('anthropic_api_key') || '';
        apiKeyInput.addEventListener('change', () => {
            localStorage.setItem('anthropic_api_key', apiKeyInput.value.trim());
        });

        // Paste handling — works anywhere on the page
        document.addEventListener('paste', handlePaste);

        const pasteZone = document.getElementById('pasteZone');
        pasteZone.addEventListener('click', () => pasteZone.focus());

        function handlePaste(e) {
            const items = e.clipboardData?.items;
            if (!items) return;
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    processImage(file, item.type);
                    break;
                }
            }
        }

        function processImage(file, mimeType) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const dataUrl = e.target.result;
                const preview = document.getElementById('preview');
                preview.src = dataUrl;
                preview.style.display = 'block';

                const pasteZone = document.getElementById('pasteZone');
                pasteZone.classList.add('active');

                extractData(dataUrl, mimeType || 'image/png');
            };
            reader.readAsDataURL(file);
        }

        async function extractData(dataUrl, mimeType) {
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) {
                showError('Vul eerst je Anthropic API key in.');
                return;
            }

            document.getElementById('loading').style.display = 'flex';
            document.getElementById('resultCard').style.display = 'none';
            document.getElementById('error').style.display = 'none';

            const base64 = dataUrl.split(',')[1];

            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: base64, mime_type: mimeType, api_key: apiKey })
                });

                if (!response.ok) {
                    let msg = response.statusText;
                    try {
                        const err = await response.json();
                        msg = err.error || msg;
                    } catch {
                        msg = await response.text().catch(() => msg);
                    }
                    throw new Error(msg);
                }

                currentData = await response.json();
                showResult();
            } catch (err) {
                showError('Fout: ' + err.message);
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }

        function setGender(gender) {
            currentGender = gender;
            document.getElementById('btnMevrouw').classList.toggle('active', gender === 'Mevrouw');
            document.getElementById('btnDhr').classList.toggle('active', gender === 'De heer');
            updateBlock();
        }

        function updateBlock() {
            const { achternaam, telefoon, email } = currentData;
            const lines = [
                `${currentGender} ${achternaam || '?'}`,
                telefoon || '?',
                email || '?'
            ];
            document.getElementById('contactBlock').textContent = lines.join('\n');

            const tel = (telefoon || '').replace(/[\s\-]/g, '');
            document.getElementById('callBtn').href = tel ? `tel:${tel}` : '#';
        }

        function showResult() {
            document.getElementById('pasteZone').classList.add('active');
            document.getElementById('resultCard').style.display = 'block';
            updateBlock();
        }

        async function copyBlock() {
            const text = document.getElementById('contactBlock').textContent;
            await navigator.clipboard.writeText(text);
            const btn = document.getElementById('copyBtn');
            btn.textContent = 'Gekopieerd!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.textContent = 'Kopieer';
                btn.classList.remove('copied');
            }, 2000);
        }

        function showError(msg) {
            const el = document.getElementById('error');
            el.textContent = msg;
            el.style.display = 'block';
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return HTML


@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json()
    image_b64 = data.get('image', '')
    mime_type = data.get('mime_type', 'image/png')
    api_key = data.get('api_key', '') or os.environ.get('ANTHROPIC_API_KEY', '')

    if not api_key:
        return jsonify({'error': 'Geen API key opgegeven'}), 400

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=256,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': mime_type,
                        'data': image_b64,
                    }
                },
                {
                    'type': 'text',
                    'text': (
                        'Extract from this image: the surname/last name only (achternaam, NOT the first name), '
                        'phone number (telefoon), and email address (email). '
                        'Return ONLY valid JSON with exactly these keys: '
                        '{"achternaam": "...", "telefoon": "...", "email": "..."}. '
                        'Use null for any field not found. No explanation, just JSON.'
                    )
                }
            ]
        }]
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    text = message.content[0].text.strip()
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
        except json.JSONDecodeError:
            result = {'achternaam': None, 'telefoon': None, 'email': None}
    else:
        result = {'achternaam': None, 'telefoon': None, 'email': None}

    return jsonify(result)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'\nContact Extractor draait op http://localhost:{port}\n')
    app.run(host='0.0.0.0', port=port, debug=False)
