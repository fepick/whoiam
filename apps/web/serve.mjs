// 기존 목업 명령은 가상 데이터의 Python 로컬 데모로 연결한다.
import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root=fileURLToPath(new URL('../../',import.meta.url));
const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=existsSync(localPython)?localPython:'python';
const server=spawn(python,['-m','apps.server','--demo=True'],{cwd:root,stdio:'inherit',windowsHide:true});
server.on('error',()=>{console.error('Python 환경과 requirements.txt 설치를 확인해주세요.');process.exitCode=1;});
server.on('exit',code=>{process.exitCode=code??1;});
process.on('SIGINT',()=>server.kill('SIGINT'));
process.on('SIGTERM',()=>server.kill('SIGTERM'));
