"use strict";

// The image and its HTML display share one projective camera transform.
(() => {
  const journey = document.querySelector(".laptop-journey");
  if (!journey) return;
  const stage = journey.querySelector(".journey-stage");
  const world = journey.querySelector(".workstation-world");
  const surface = journey.querySelector(".laptop-screen-surface");
  const arrival = journey.querySelector(".screen-arrival");
  const intro = journey.querySelector(".journey-copy");
  const enter = journey.querySelector(".journey-enter");
  const introLinks = [...intro.querySelectorAll("a, button")];
  const header = document.querySelector(".site-header");
  const step = journey.querySelector(".journey-step");
  const story = journey.querySelector(".journey-story");
  const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
  // Inner corners of the blank display in the 1536 x 1024 scene artwork.
  const screenCorners = [[945,306],[1354,351],[1285,665],[879,553]];
  const clamp = (v) => Math.max(0, Math.min(1, v));
  const ease = (v) => { const x = clamp(v); return x * x * (3 - 2 * x); };
  const mix = (a,b,t) => a + (b-a)*t;
  const interpolate = (a,b,t) => a.map((point,i) => point.map((value,j) => mix(value,b[i][j],t)));
  let queued = false;
  let lastPhase = "";
  let interactive = false;
  let enterRequested = false;
  let renderedProgress = null;
  let lastFrameTime = 0;

  function project(source, target) {
    const rows = [];
    source.forEach(([x,y],i) => {
      const [u,v] = target[i];
      rows.push([x,y,1,0,0,0,-u*x,-u*y,u]);
      rows.push([0,0,0,x,y,1,-v*x,-v*y,v]);
    });
    for (let col=0;col<8;col++) {
      let best=col;
      for (let row=col+1;row<8;row++) if(Math.abs(rows[row][col])>Math.abs(rows[best][col])) best=row;
      [rows[col],rows[best]]=[rows[best],rows[col]];
      const divisor=rows[col][col];
      if(Math.abs(divisor)<1e-10) return null;
      for(let j=col;j<9;j++) rows[col][j]/=divisor;
      for(let row=0;row<8;row++) {
        if(row===col) continue;
        const factor=rows[row][col];
        for(let j=col;j<9;j++) rows[row][j]-=factor*rows[col][j];
      }
    }
    const h=rows.map(row=>row[8]);
    return "matrix3d("+[h[0],h[3],0,h[6],h[1],h[4],0,h[7],0,0,1,0,h[2],h[5],0,1].join(",")+")";
  }
  const mappedScreen = project([[0,0],[800,0],[800,500],[0,500]],screenCorners);
  if(!mappedScreen) return;
  surface.style.transform=mappedScreen;
  document.documentElement.dataset.camera="ready";

  function disabled() { return preference.matches || document.documentElement.dataset.motion!=="on"; }
  function draw(timestamp = performance.now()) {
    queued=false;
    const off=disabled();
    if(off) enterRequested=false;
    const headerHeight=header?.offsetHeight ?? 0;
    journey.style.setProperty("--entry-header-height",headerHeight+"px");
    const width=stage.clientWidth;
    const height=stage.clientHeight;
    const compact=width<=760;
    const distance=Math.max(1,journey.offsetHeight-height);
    const journeyRect=journey.getBoundingClientRect();
    const raw=off ? 0 : clamp((headerHeight-journeyRect.top)/distance);
    // Follow wheel steps with a short, frame-rate-independent camera ease.
    // Native page scrolling stays untouched; stop requesting frames at rest.
    const targetProgress=clamp(raw/.82);
    const outside=journeyRect.bottom<=headerHeight || journeyRect.top>=window.innerHeight;
    const elapsed=Math.min(64,Math.max(1,timestamp-lastFrameTime || 16.67));
    lastFrameTime=timestamp;
    if(renderedProgress===null || off || outside) renderedProgress=targetProgress;
    else renderedProgress+=(targetProgress-renderedProgress)*(1-Math.exp(-elapsed/95));
    if(Math.abs(targetProgress-renderedProgress)<.0001) renderedProgress=targetProgress;
    const p=renderedProgress;
    const baseScale=compact ? Math.min(width*1.13/1536,height*.53/1024) : Math.min(width*.83/1536,height*.99/1024);
    const originX=width*(compact?.50:.70)-1536*baseScale/2;
    const originY=compact ? height*.50 : height*.51-1024*baseScale/2;
    const first=screenCorners.map(([x,y])=>[originX+x*baseScale,originY+y*baseScale]);
    const orbitWidth=Math.min(width*(compact?.90:.59),height*1.06);
    const orbitHeight=orbitWidth/1.6;
    const cx=width*(compact?.52:.59),cy=height*(compact?.56:.51);
    const orbit=[
      [cx-orbitWidth*.50,cy-orbitHeight*.35],
      [cx+orbitWidth*.50,cy-orbitHeight*.65],
      [cx+orbitWidth*.42,cy+orbitHeight*.40],
      [cx-orbitWidth*.56,cy+orbitHeight*.60]
    ];
    const cover=Math.max(width/800,height/500)*1.1;
    const rectangle=(factor)=>{
      const w=800*cover*factor,h=500*cover*factor;
      return [[(width-w)/2,(height-h)/2],[(width+w)/2,(height-h)/2],[(width+w)/2,(height+h)/2],[(width-w)/2,(height+h)/2]];
    };
    let target;
    if(p<.42) target=interpolate(first,orbit,ease(p/.42));
    else if(p<.87) target=interpolate(orbit,rectangle(1),ease((p-.42)/.45));
    else target=interpolate(rectangle(1),rectangle(1.10),ease((p-.87)/.13));
    const camera=project(screenCorners,target);
    if(camera) world.style.transform=camera;
    const copyOpacity=1-ease((p-.05)/.20);
    // Separate entry/exit thresholds prevent flicker on tiny reverse scrolls.
    const ready=!off && (interactive ? p>=.84 : p>=.885);
    const arrivalOpacity=ready ? 1 : 0;
    const vars={
      "--intro-opacity":String(copyOpacity),
      "--intro-y":(-ease(p/.3)*26)+"px",
      "--arrival-opacity":String(arrivalOpacity),
      "--scene-opacity":String(1-arrivalOpacity),
      "--room-yaw":(22-Math.sin(p*Math.PI)*65)+"deg",
      "--room-roll":(-Math.sin(p*Math.PI)*9)+"deg",
      "--room-depth":(p*120)+"px",
      "--journey-progress":p*100+"%"
    };
    Object.entries(vars).forEach(([key,value])=>journey.style.setProperty(key,value));
    // Keep the page h1 available to assistive technology throughout the journey.
    intro.dataset.hidden=String(copyOpacity<.02);
    introLinks.forEach(link=>{link.inert=copyOpacity<.02;});
    arrival.dataset.visible=String(arrivalOpacity>0);
    if(ready!==interactive) {
      if(!ready && arrival.contains(document.activeElement)) {
        const focusTarget=intro.dataset.hidden==="true" ? document.querySelector(".site-header .wordmark") : enter;
        focusTarget?.focus({preventScroll:true});
      }
      arrival.inert=!ready;
      arrival.setAttribute("aria-hidden",String(!ready));
      interactive=ready;
      if(ready && enterRequested) {
        arrival.querySelector("a")?.focus({preventScroll:true});
        enterRequested=false;
      }
    }
    const phase=off?"static":ready?"inside":p<.20?"desk":p<.53?"orbit":"dive";
    if(phase!==lastPhase) {
      const labels={
        static:["EXPLORE AT YOUR PACE","아래에서 프로젝트와 자기소개를 선택하세요."],
        desk:["01 / AT THE DESK","스크롤해 작업 공간 안으로 들어오세요."],
        orbit:["02 / A NEW PERSPECTIVE","시선을 돌려 노트북 화면으로."],
        dive:["03 / INTO THE SCREEN","생각이 기록이 되는 곳으로."],
        inside:["04 / INSIDE THE FIELD NOTES","원하는 이야기를 선택하세요. 위로 스크롤하면 돌아갑니다."]
      }[phase];
      step.textContent=labels[0];story.textContent=labels[1];lastPhase=phase;
    }
    if(renderedProgress!==targetProgress) schedule();
  }
  function schedule(){if(!queued){queued=true;requestAnimationFrame(draw);}}
  enter.addEventListener("click",event=>{
    if(event.button!==0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || disabled()) return;
    event.preventDefault();
    enterRequested=true;
    const headerHeight=header?.offsetHeight ?? 0;
    const start=window.scrollY+journey.getBoundingClientRect().top-headerHeight;
    window.scrollTo({top:start+(journey.offsetHeight-stage.offsetHeight)*.9,behavior:"smooth"});
  });
  window.addEventListener("scroll",schedule,{passive:true});
  window.addEventListener("resize",schedule);
  preference.addEventListener("change",schedule);
  new MutationObserver(schedule).observe(document.documentElement,{attributes:true,attributeFilter:["data-motion"]});
  draw();
})();
