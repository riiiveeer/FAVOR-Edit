"""Standalone bundled-Matplotlib renderer: fixed axes and deterministic SVG/PNG."""
import json
import sys
from pathlib import Path


def render(data_path, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import numpy as np
    from PIL import Image
    data=json.loads(Path(data_path).read_text(encoding='utf-8'))
    cfg=data['config']; spec=cfg['figures']; output=Path(output); output.mkdir(parents=True,exist_ok=True)
    font=None
    for family in cfg['font_fallback']:
        try:
            path=font_manager.findfont(family,fallback_to_default=False)
            font=family; break
        except ValueError: pass
    if not font: raise ValueError('required Chinese font is unavailable')
    plt.rcParams.update({'font.family':font,'font.size':14,'axes.unicode_minus':False,'svg.fonttype':'none',
                         'svg.hashsalt':cfg['protocol'],'axes.spines.top':False,'axes.spines.right':False})
    width,height=spec['width'],spec['height']; dpi=spec['dpi']
    def figure(): return plt.subplots(figsize=(width/dpi,height/dpi),dpi=dpi)
    def save(fig,name):
        fig.savefig(output/(name+'.svg'),metadata={'Date':None,'Creator':'defense-report-v1'},facecolor=spec['background'])
        fig.savefig(output/(name+'.png'),dpi=dpi,facecolor=spec['background'],metadata={'Software':'defense-report-v1'})
        plt.close(fig)
        with Image.open(output/(name+'.png')) as im:
            if im.size!=(width,height): raise ValueError('figure dimensions drift')
    main=[r for r in data['main'] if r['field']=='overall']; labels=['Proposed N=4 vs N=1','Proposed N=4 vs Linear N=4']
    fig,ax=figure(); fig.subplots_adjust(left=.29,right=.94,top=.78,bottom=.22)
    for i,row in enumerate(main):
        y=1-i; value=float(row['tie_aware_win_rate']); lo=float(row['bootstrap_lower']); hi=float(row['bootstrap_upper'])
        ax.errorbar(value,y,xerr=[[value-lo],[hi-value]],fmt='o',capsize=8,color='#0072B2',markersize=10,linewidth=3)
        ax.text(value,y+.19,f"{value:.3f}  [{lo:.3f}, {hi:.3f}]",ha='center',fontsize=16)
    ax.axvline(spec['reference'],color='#555555',linestyle='--',linewidth=1.5,label='0.5 参考线')
    ax.set(xlim=spec['ci_axis'],ylim=(-.5,1.5),yticks=[1,0],yticklabels=[f"{label}\nn={r['total']}" for label,r in zip(labels,main)],xlabel='tie-aware win rate（全部比较）')
    ax.set_xticks(np.linspace(0,1,6)); ax.grid(axis='x',alpha=.18)
    fig.suptitle('描述性总体偏好与任务级不确定性',fontsize=23,y=.94)
    fig.text(.5,.06,f"{data['facts']['sample_clusters']['display']} clusters / {data['facts']['bootstrap_iterations']['display']} bootstrap / 95% CI；两区间均跨 0.5",ha='center',fontsize=14)
    save(fig,'overall-ci')
    fig,ax=figure(); fig.subplots_adjust(left=.29,right=.94,top=.78,bottom=.23)
    for i,row in enumerate(main):
        left=0
        for field,key,label in [('wins','win','胜 W'),('losses','loss','负 L'),('ties','tie','平 T'),('uncertain','uncertain','不确定 U')]:
            value=int(row[field]); ax.barh(1-i,value,left=left,color=spec['colors'][key],height=.48,label=label if i==0 else None,hatch='//' if key=='uncertain' else None,edgecolor='white')
            if value: ax.text(left+value/2,1-i,str(value),ha='center',va='center',color='white' if key in ('win','loss') else '#101820',fontsize=19,bbox=None)
            left+=value
    ax.set(xlim=spec['outcome_axis'],yticks=[1,0],yticklabels=labels,xlabel='唯一 comparison 数量'); ax.set_xticks(range(0,29,7))
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.2),ncol=4,frameon=False)
    fig.suptitle('平局与不确定分别保留',fontsize=23,y=.94)
    fig.text(.5,.83,'overall / all-42；两 family 分母为28与14',ha='center',fontsize=15)
    save(fig,'outcomes')
    fig,ax=figure(); fig.subplots_adjust(left=.14,right=.97,top=.77,bottom=.25)
    rows=data['agreement'][:5]; x=np.arange(5)
    ax.plot(x,[float(r['observed_agreement']) for r in rows],'o-',color='#0072B2',label='observed agreement',linewidth=2,markersize=8)
    ax.plot(x,[float(r['cohen_kappa']) for r in rows],'s--',color='#D55E00',label="Cohen's kappa",linewidth=2,markersize=8)
    for i,row in enumerate(rows):
        for key,dy in [('observed_agreement',.08),('cohen_kappa',-.12)]: ax.text(i,float(row[key])+dy,f"{float(row[key]):.3f}",ha='center',fontsize=13)
    ax.set(ylim=spec['agreement_axis'],xticks=x,xticklabels=['总体偏好','指令忠实度','非目标保持','时序一致性','视觉质量'])
    ax.axhline(0,color='#777777',linewidth=1); ax.grid(axis='y',alpha=.18)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.19),ncol=2,frameon=False)
    fig.suptitle('双人一致性较低，自动平局不进入分母',fontsize=23,y=.94)
    fig.text(.5,.83,'32 个 manual comparison；agreement与机会校正kappa分别解释',ha='center',fontsize=14)
    save(fig,'agreement')
    fig,ax=figure(); ax.axis('off'); fig.subplots_adjust(left=.03,right=.97,top=.85,bottom=.08)
    nodes=data['flow']; positions=[(.1,.78),(.37,.78),(.66,.78),(.9,.78),(.75,.32),(.43,.32),(.12,.32)]
    for i,(label,(x,y)) in enumerate(zip(nodes,positions)):
        ax.text(x,y,label.replace(' 嵌套','\n嵌套'),ha='center',va='center',fontsize=15,bbox={'boxstyle':'square,pad=.55','fc':'#F5F7FA','ec':'#0072B2','lw':1.5})
        if i:
            px,py=positions[i-1]
            ax.annotate('',xy=(x,y),xytext=(px,py),arrowprops={'arrowstyle':'->','color':'#666666','lw':1.5,'shrinkA':70,'shrinkB':75})
    fig.suptitle('只读输入到可追溯报告',fontsize=25,y=.95)
    fig.text(.5,.07,'固定协议、媒体身份、方法角色与输出清单逐级校验',ha='center',fontsize=17)
    save(fig,'system-flow')
    import hashlib
    receipt={'font_family':font,'font_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'matplotlib':matplotlib.__version__,'numpy':np.__version__,'size':[width,height],'dpi':dpi}
    (output/'figure-render.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': render(sys.argv[1],sys.argv[2])
