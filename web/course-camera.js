// Presentation only: the camera and every overlay use the same saved world coordinates.
const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));

export function courseCamera(course,game,zoom,aspect=2) {
  const [x,y,w,h]=course.viewbox??[-20,-85,410,170];
  aspect=Number.isFinite(aspect)&&aspect>0?aspect:w/h;
  let width,height,cx,cy;
  if(zoom){
    height=Math.min(48,h,w/aspect);width=height*aspect;
    cx=course.pin[1];cy=course.pin[0];
  }else{
    // Fill the wide panel by cropping peripheral scenery, retaining tee-to-pin framing.
    width=w;height=w/aspect;cx=x+w/2;
    const points=[course.tee,course.pin,...(course.playing_line??[]),game.position];
    const ys=points.map(p=>p[0]);
    const top=Math.min(...ys)-8,bottom=Math.max(...ys)+8;
    cy=clamp(y+h/2,bottom-height/2,top+height/2);
    // Narrow screens show the complete hole; CSS uses the course's natural aspect ratio.
    if(height>h)return [x,y,w,h];
  }
  return [clamp(cx-width/2,x,x+w-width),clamp(cy-height/2,y,y+h-height),width,height];
}

let observer;
export function fitCourseCamera(svg,data,zoom) {
  observer?.disconnect();
  let watcher;
  const update=()=>{
    if(!svg.isConnected){watcher?.disconnect();return;}
    const {width,height}=svg.getBoundingClientRect();
    if(width&&height)svg.setAttribute('viewBox',courseCamera(data.course,data.game,zoom,width/height).join(' '));
  };
  update();watcher=new ResizeObserver(update);observer=watcher;watcher.observe(svg);
}
