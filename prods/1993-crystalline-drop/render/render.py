import asyncio, sys, base64, subprocess
from playwright.async_api import async_playwright
MODE=sys.argv[1]
FPS=30; DUR=240.0
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1080,'height':675})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('http://localhost:8770/render.html'); await pg.wait_for_timeout(2500)
        await pg.evaluate("document.fonts.ready"); await pg.evaluate("__R.init()")
        if MODE=='test':
            for t0 in [17,40,125,170,200,236]:
                for k in range(20): await pg.evaluate(f"__R.step({t0-20/30+k/30},{1/30})")
                d=await pg.evaluate(f"__R.step({t0},{1/30})")
                open(f'test_{t0}.jpg','wb').write(base64.b64decode(d.split(',')[1]))
        else:
            ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','image2pipe','-framerate',str(FPS),'-c:v','mjpeg','-i','-','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','video_only.mp4'],stdin=subprocess.PIPE)
            n=int(DUR*FPS)
            for i in range(n):
                d=await pg.evaluate(f"__R.step({i/FPS},{1/FPS})")
                ff.stdin.write(base64.b64decode(d.split(',')[1]))
                if i%300==0: print('frame',i,'/',n,flush=True)
            ff.stdin.close(); ff.wait()
        print('errors',errs[:5],flush=True)
        await b.close()
asyncio.run(main())
