R=5.09
units={1:[(25,349),(150,299)],2:[(150,299),(700,279)],3:[(2000,259)],4:[(4000,249)],5:[(7000,239)]}
cogs={1:[190,150],2:[150,110],3:[80],4:[65],5:[60]}
avgbase={1:0,2:600,3:2000,4:5000,5:10500}
lic={1:0,2:0,3:20000,4:40000,5:60000}
rd={1:68000,2:79000,3:106000,4:120000,5:140000}
comfix={1:15000,2:40000,3:52000,4:64000,5:76000}; cac={1:30,2:30,3:25,4:22,5:20}
ga={1:10000,2:15000,3:25000,4:35000,5:45000}
capex={1:5000,2:40000,3:60000,4:30000,5:30000}
staff={1:1,2:3,3:4,4:5,5:6}
out={}; cum=0; loss=0
for y in range(1,6):
    n=sum(u for u,p in units[y]); hw=sum(u*p for u,p in units[y])
    subs=avgbase[y]*0.15*4*12; acc=0.05*hw
    rev_poc=hw+subs+acc+lic[y]
    c_hw=sum(u*c for (u,p),c in zip(units[y],cogs[y])); var=0.08*hw; c_sub=0.5*subs; c_acc=0.5*acc
    com=comfix[y]+cac[y]*n
    opex=c_hw+var+c_sub+c_acc+rd[y]+com+ga[y]
    ebitda=rev_poc-opex
    cum+=capex[y]; dep=3000+0.2*cum
    ebt=ebitda-dep
    taxable=ebt+loss if ebt>0 else 0
    if ebt<=0: loss+=ebt; tax=0
    else:
        base=ebt+loss
        if base>0: tax=0.16*base; loss=0
        else: tax=0; loss=base
    net=ebt-tax
    out[y]=dict(n=n,hw=hw,subs=subs,acc=acc,lic=lic[y],rev=rev_poc,opex=opex,rd=rd[y],com=com,ebitda=ebitda,dep=dep,tax=tax,net=net,capex=capex[y],cogs=c_hw)
    print(y, {k:round(v) for k,v in out[y].items()})
def L(x): return f"{x*R/1000:,.0f}".replace(',','.')
for y in out: print(y, L(out[y]['rev']), L(out[y]['opex']), L(out[y]['rd']), L(out[y]['com']), L(out[y]['ebitda']), L(out[y]['net']), L(out[y]['capex']))

def run(unit_f=1.0, price_f=1.0):
    res={}; cum=0; loss=0
    for y in range(1,6):
        u=[(n*unit_f, p*price_f) for n,p in units[y]]
        n=sum(a for a,b in u); hw=sum(a*b for a,b in u)
        subs=avgbase[y]*unit_f*0.15*4*12; acc=0.05*hw
        rev=hw+subs+acc+lic[y]
        c=sum(a*cc for (a,b),cc in zip(u,cogs[y]))
        opex=c+0.08*hw+0.5*subs+0.5*acc+rd[y]+comfix[y]+cac[y]*n+ga[y]
        e=rev-opex; cum+=capex[y]; dep=3000+0.2*cum; ebt=e-dep
        base=ebt+loss
        if base>0: tax=0.16*base if ebt>0 else 0; loss=0
        else: tax=0; loss=base if ebt<0 or base<0 else 0
        res[y]=dict(rev=rev,opex=opex,dep=dep,ebitda=e,net=ebt-tax)
    return res
p=run(0.5,0.9)
print('prudent', {y:(round(v['rev']),round(v['ebitda']),round(v['net'])) for y,v in p.items()})
