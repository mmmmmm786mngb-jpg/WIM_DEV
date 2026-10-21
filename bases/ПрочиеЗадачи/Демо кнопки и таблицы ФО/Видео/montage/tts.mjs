// Озвучка фраз ролика женским голосом Edge TTS: lines.json -> <id>.mp3 в этой папке.
// node-edge-tts берется из пакета web-test (~/.claude/skills/web-test/scripts/node_modules).
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { homedir } from 'os';

const here = dirname(fileURLToPath(import.meta.url));
const mod = join(homedir(), '.claude/skills/web-test/scripts/node_modules/node-edge-tts/dist/edge-tts.js');
const { EdgeTTS } = await import(pathToFileURL(mod).href);

const lines = JSON.parse(readFileSync(join(here, 'lines.json'), 'utf8'));
const tts = new EdgeTTS({ voice: 'ru-RU-SvetlanaNeural', lang: 'ru-RU', rate: '+5%', timeout: 30000 });
for (const line of lines) {
  await tts.ttsPromise(line.text, join(here, line.id + '.mp3'));
  console.log('ok', line.id);
}
