import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const exec = promisify(execFile);
export const STYLE_QUESTIONS = [
  {key:'purpose',title:'Who are your videos for, and what should they achieve?',placeholder:'Audience, topics, platform, and what viewers should do or remember.'},
  {key:'personality',title:'How should your videos feel?',placeholder:'For example: calm and minimal, bold and energetic, cinematic, playful.',choices:['Calm & minimal','Bold & energetic','Cinematic','Playful']},
  {key:'branding',title:'What colours, fonts or brand rules should we use?',placeholder:'Brand colours, font names, logos, or “choose for me”.'},
  {key:'pacing',title:'What pacing and layouts do you like?',placeholder:'Quick cuts or room to breathe? Mostly footage, split screens, or full-screen graphics?'},
  {key:'captions',title:'How should captions look?',placeholder:'Always on or occasional? Phrase or word by word? Case, size, position and highlighting.',choices:['Clean phrase captions','Bold word-by-word captions','Subtle subtitles','No captions']},
  {key:'graphicsAudio',title:'What graphics, music and sound effects fit?',placeholder:'Charts, callouts, screenshots, animations, transitions, music mood, and how much SFX.'},
  {key:'boundaries',title:'Anything you love, dislike, or want kept consistent?',placeholder:'Hook and ending preferences, examples you like, things to avoid, or other must-haves.'},
];
export async function extractStyleDocument(file) {
  if(fs.statSync(file).size > 25*1024*1024)throw new Error('Style documents must be under 25 MB.');
  const ext=path.extname(file).toLowerCase();let text;
  try {
    if(['.txt','.md'].includes(ext))text=fs.readFileSync(file,'utf8');
    else if(ext==='.docx') {
      const script='import sys,zipfile,xml.etree.ElementTree as E\nwith zipfile.ZipFile(sys.argv[1]) as z:\n names=[n for n in z.namelist() if n=="word/document.xml" or n.startswith(("word/header","word/footer")) and n.endswith(".xml")]\n print("\\n".join(" ".join(e.itertext()) for n in names for e in E.fromstring(z.read(n)).iter() if e.tag.endswith("}p")))';
      text=(await exec('python3',['-c',script,file],{timeout:30000,maxBuffer:2*1024*1024})).stdout;
    } else if(ext==='.pdf') {
      const script='import sys\nfrom pypdf import PdfReader\nr=PdfReader(sys.argv[1])\nprint("\\n".join(p.extract_text() or "" for p in r.pages))';
      try {text=(await exec('python3',['-c',script,file],{timeout:30000,maxBuffer:2*1024*1024})).stdout;}
      catch(error) {
        if(!/No module named.*pypdf/.test(error.stderr || ''))throw error;
        text=(await exec('uv',['run','--with','pypdf','python','-c',script,file],{timeout:90000,maxBuffer:2*1024*1024})).stdout;
      }
    } else throw new Error('Upload a PDF, DOCX, TXT or Markdown document.');
  } catch(error) {throw new Error(`Could not read ${path.basename(file)}. PDF extraction needs pypdf or uv; DOCX extraction needs Python 3. Try a TXT or Markdown version. ${error.code === 'ENOENT' ? 'Required command not found.' : ''}`);}
  if(!text?.trim())throw new Error('This document has no extractable text. For a scanned PDF, upload images as references or a text version.');
  if(text.length > 120000)throw new Error('This document is too long. Upload a shorter style or brand guide.');
  return text.trim();
}
