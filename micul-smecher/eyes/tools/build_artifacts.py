"""Inline eyes.js + designs.js into one.html / index.html for single-file publishing.
   python3 tools/build_artifacts.py OUT_DIR"""
import re, sys, os
here=os.path.join(os.path.dirname(__file__),'..')
out=sys.argv[1]
js=open(os.path.join(here,'eyes.js')).read()
ds=open(os.path.join(here,'designs.js')).read()
for src,dst in [('one.html','soul-signature-eyes.html'),('index.html','soul-eye-collection.html')]:
    s=open(os.path.join(here,src)).read()
    s=s.replace('<script src="eyes.js"></script>','<script>\n'+js.replace('</script>','<\\/script>')+'\n</script>')
    s=s.replace('<script src="designs.js"></script>','<script>\n'+ds+'\n</script>')
    s=re.sub(r'<!doctype html>\s*<html[^>]*>\s*<head>\s*<meta charset="utf-8">\s*<meta name="viewport"[^>]*>\s*','',s)
    s=s.replace('</head>\n<body>\n','').replace('</body>\n</html>\n','')
    assert s.startswith('<title>') and 'src="eyes.js"' not in s
    open(os.path.join(out,dst),'w').write(s); print(dst,len(s))
