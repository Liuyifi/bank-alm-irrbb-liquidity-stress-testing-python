"""QA thumbnails only; full-resolution PNGs remain available for targeted review."""
from PIL import Image,ImageDraw
from .config import ROOT


def build():
    files=sorted((ROOT/'qa/render').glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
    for start in range(0,len(files),3):
        canvas=Image.new('RGB',(2100,1040),'#dce2e8');draw=ImageDraw.Draw(canvas)
        for j,f in enumerate(files[start:start+3]):
            im=Image.open(f).convert('RGB');im.thumbnail((680,990));canvas.paste(im,(j*700+10,35));draw.text((j*700+12,10),f.stem,fill='black')
        canvas.save(ROOT/f'qa/word_contact_{start//3+1}.png')
    files=sorted((ROOT/'qa/workbook_previews').glob('*.png'))
    for start in range(0,len(files),4):
        canvas=Image.new('RGB',(1600,1160),'#dce2e8');draw=ImageDraw.Draw(canvas)
        for j,f in enumerate(files[start:start+4]):
            im=Image.open(f).convert('RGB');im.thumbnail((785,530));x=(j%2)*800;y=(j//2)*580
            draw.text((x+15,y+8),f.stem,fill='black');canvas.paste(im,(x+8,y+34))
        canvas.save(ROOT/f'qa/workbook_contact_{start//4+1}.png')


if __name__=='__main__':build()
