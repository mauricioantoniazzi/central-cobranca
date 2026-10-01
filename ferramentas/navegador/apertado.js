(function(){
  const SKIP=/^(TD|TH|TR|TABLE|TBODY|SVG|BODY|HTML|MAIN|A|SPAN|B|I|OPTION|SELECT|TEXTAREA|INPUT|BUTTON|DETAILS|SUMMARY|LI|UL|LABEL|P|H1|H2|H3|DIV)$/;
  const cartao=el=>{const cs=getComputedStyle(el);const bw=parseFloat(cs.borderLeftWidth)+parseFloat(cs.borderRightWidth)+parseFloat(cs.borderTopWidth)+parseFloat(cs.borderBottomWidth);
    const bg=cs.backgroundColor!=='rgba(0, 0, 0, 0)'&&cs.backgroundColor!=='transparent';
    const pequeno=['tag','chip','origem','idx','sw','bar'].some(c=>el.classList.contains(c));
    return (bw>0&&cs.borderLeftStyle!=='none'||bg)&&!pequeno&&el.tagName!=='TABLE'&&!/^(TD|TH|TR|TBODY|OPTION|INPUT|SELECT|TEXTAREA|BUTTON|SUMMARY)$/.test(el.tagName)&&el!==document.body&&el.tagName!=='MAIN'&&el.tagName!=='HTML'&&el.tagName!=='SVG'&&!el.closest('svg');};
  const out=[];const vistos=new Set();
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  let n;while(n=walker.nextNode()){
    if(!n.textContent.trim())continue;const pai=n.parentElement;if(!pai||pai.closest('svg,script,style,textarea'))continue;
    let c=pai;while(c&&!cartao(c))c=c.parentElement;if(!c)continue;
    const rg=document.createRange();rg.selectNodeContents(n);const cr=c.getBoundingClientRect();
    for(const r of rg.getClientRects()){if(r.width<1)continue;
      const esq=r.left-cr.left,dir=cr.right-r.right,topo=r.top-cr.top,base=cr.bottom-r.bottom;
      const m=Math.min(esq,dir);
      if(m<10||topo<5||base<5){const k=(c.className||c.tagName)+'|'+n.textContent.trim().slice(0,18);if(vistos.has(k))continue;vistos.add(k);
        out.push({cartao:(c.tagName+'.'+(c.className||'')).slice(0,30),texto:n.textContent.trim().slice(0,28),esq:Math.round(esq),dir:Math.round(dir),topo:Math.round(topo),base:Math.round(base)});}}
  }
  return JSON.stringify(out);
})()
