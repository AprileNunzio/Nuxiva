/**
 * @license
 * Copyright 2010-2023 Three.js Authors
 * SPDX-License-Identifier: MIT
 */const Es="162",Hm={ROTATE:0,DOLLY:1,PAN:2},Vm={ROTATE:0,PAN:1,DOLLY_PAN:2,DOLLY_ROTATE:3},Cl=0,Hs=1,Pl=2,Co=1,Ll=2,$e=3,pn=0,Ee=1,je=2,hn=0,ni=1,Vs=2,ks=3,Ws=4,Dl=5,bn=100,Ul=101,Il=102,Xs=103,qs=104,Nl=200,Fl=201,Ol=202,Bl=203,hs=204,us=205,zl=206,Gl=207,Hl=208,Vl=209,kl=210,Wl=211,Xl=212,ql=213,Yl=214,Jl=0,Zl=1,Kl=2,lr=3,$l=4,jl=5,Ql=6,tc=7,Po=0,ec=1,nc=2,un=0,ic=1,rc=2,sc=3,ac=4,oc=5,lc=6,cc=7,Lo=300,ri=301,si=302,fs=303,ds=304,mr=306,ps=1e3,Ne=1001,ms=1002,de=1003,Ys=1004,di=1005,ye=1006,wr=1007,Rn=1008,fn=1009,hc=1010,uc=1011,Ts=1012,Do=1013,cn=1014,He=1015,Ai=1016,Uo=1017,Io=1018,Cn=1020,fc=1021,Fe=1023,dc=1024,pc=1025,Pn=1026,ai=1027,No=1028,Fo=1029,mc=1030,Oo=1031,Bo=1033,Rr=33776,Cr=33777,Pr=33778,Lr=33779,Js=35840,Zs=35841,Ks=35842,$s=35843,zo=36196,js=37492,Qs=37496,ta=37808,ea=37809,na=37810,ia=37811,ra=37812,sa=37813,aa=37814,oa=37815,la=37816,ca=37817,ha=37818,ua=37819,fa=37820,da=37821,Dr=36492,pa=36494,ma=36495,gc=36283,ga=36284,_a=36285,va=36286,_c=3200,vc=3201,Go=0,xc=1,ln="",ze="srgb",mn="srgb-linear",As="display-p3",gr="display-p3-linear",cr="linear",$t="srgb",hr="rec709",ur="p3",Nn=7680,xa=519,Mc=512,Sc=513,yc=514,Ho=515,Ec=516,Tc=517,Ac=518,bc=519,Ma=35044,Sa="300 es",gs=1035,Qe=2e3,fr=2001;class li{addEventListener(t,e){this._listeners===void 0&&(this._listeners={});const n=this._listeners;n[t]===void 0&&(n[t]=[]),n[t].indexOf(e)===-1&&n[t].push(e)}hasEventListener(t,e){if(this._listeners===void 0)return!1;const n=this._listeners;return n[t]!==void 0&&n[t].indexOf(e)!==-1}removeEventListener(t,e){if(this._listeners===void 0)return;const r=this._listeners[t];if(r!==void 0){const s=r.indexOf(e);s!==-1&&r.splice(s,1)}}dispatchEvent(t){if(this._listeners===void 0)return;const n=this._listeners[t.type];if(n!==void 0){t.target=this;const r=n.slice(0);for(let s=0,o=r.length;s<o;s++)r[s].call(this,t);t.target=null}}}const ge=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"];let ya=1234567;const Si=Math.PI/180,bi=180/Math.PI;function Un(){const i=Math.random()*4294967295|0,t=Math.random()*4294967295|0,e=Math.random()*4294967295|0,n=Math.random()*4294967295|0;return(ge[i&255]+ge[i>>8&255]+ge[i>>16&255]+ge[i>>24&255]+"-"+ge[t&255]+ge[t>>8&255]+"-"+ge[t>>16&15|64]+ge[t>>24&255]+"-"+ge[e&63|128]+ge[e>>8&255]+"-"+ge[e>>16&255]+ge[e>>24&255]+ge[n&255]+ge[n>>8&255]+ge[n>>16&255]+ge[n>>24&255]).toLowerCase()}function ae(i,t,e){return Math.max(t,Math.min(e,i))}function bs(i,t){return(i%t+t)%t}function wc(i,t,e,n,r){return n+(i-t)*(r-n)/(e-t)}function Rc(i,t,e){return i!==t?(e-i)/(t-i):0}function yi(i,t,e){return(1-e)*i+e*t}function Cc(i,t,e,n){return yi(i,t,1-Math.exp(-e*n))}function Pc(i,t=1){return t-Math.abs(bs(i,t*2)-t)}function Lc(i,t,e){return i<=t?0:i>=e?1:(i=(i-t)/(e-t),i*i*(3-2*i))}function Dc(i,t,e){return i<=t?0:i>=e?1:(i=(i-t)/(e-t),i*i*i*(i*(i*6-15)+10))}function Uc(i,t){return i+Math.floor(Math.random()*(t-i+1))}function Ic(i,t){return i+Math.random()*(t-i)}function Nc(i){return i*(.5-Math.random())}function Fc(i){i!==void 0&&(ya=i);let t=ya+=1831565813;return t=Math.imul(t^t>>>15,t|1),t^=t+Math.imul(t^t>>>7,t|61),((t^t>>>14)>>>0)/4294967296}function Oc(i){return i*Si}function Bc(i){return i*bi}function _s(i){return(i&i-1)===0&&i!==0}function zc(i){return Math.pow(2,Math.ceil(Math.log(i)/Math.LN2))}function dr(i){return Math.pow(2,Math.floor(Math.log(i)/Math.LN2))}function Gc(i,t,e,n,r){const s=Math.cos,o=Math.sin,a=s(e/2),l=o(e/2),c=s((t+n)/2),h=o((t+n)/2),u=s((t-n)/2),d=o((t-n)/2),m=s((n-t)/2),_=o((n-t)/2);switch(r){case"XYX":i.set(a*h,l*u,l*d,a*c);break;case"YZY":i.set(l*d,a*h,l*u,a*c);break;case"ZXZ":i.set(l*u,l*d,a*h,a*c);break;case"XZX":i.set(a*h,l*_,l*m,a*c);break;case"YXY":i.set(l*m,a*h,l*_,a*c);break;case"ZYZ":i.set(l*_,l*m,a*h,a*c);break;default:console.warn("THREE.MathUtils: .setQuaternionFromProperEuler() encountered an unknown order: "+r)}}function jn(i,t){switch(t.constructor){case Float32Array:return i;case Uint32Array:return i/4294967295;case Uint16Array:return i/65535;case Uint8Array:return i/255;case Int32Array:return Math.max(i/2147483647,-1);case Int16Array:return Math.max(i/32767,-1);case Int8Array:return Math.max(i/127,-1);default:throw new Error("Invalid component type.")}}function Me(i,t){switch(t.constructor){case Float32Array:return i;case Uint32Array:return Math.round(i*4294967295);case Uint16Array:return Math.round(i*65535);case Uint8Array:return Math.round(i*255);case Int32Array:return Math.round(i*2147483647);case Int16Array:return Math.round(i*32767);case Int8Array:return Math.round(i*127);default:throw new Error("Invalid component type.")}}const km={DEG2RAD:Si,RAD2DEG:bi,generateUUID:Un,clamp:ae,euclideanModulo:bs,mapLinear:wc,inverseLerp:Rc,lerp:yi,damp:Cc,pingpong:Pc,smoothstep:Lc,smootherstep:Dc,randInt:Uc,randFloat:Ic,randFloatSpread:Nc,seededRandom:Fc,degToRad:Oc,radToDeg:Bc,isPowerOfTwo:_s,ceilPowerOfTwo:zc,floorPowerOfTwo:dr,setQuaternionFromProperEuler:Gc,normalize:Me,denormalize:jn};class it{constructor(t=0,e=0){it.prototype.isVector2=!0,this.x=t,this.y=e}get width(){return this.x}set width(t){this.x=t}get height(){return this.y}set height(t){this.y=t}set(t,e){return this.x=t,this.y=e,this}setScalar(t){return this.x=t,this.y=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y)}copy(t){return this.x=t.x,this.y=t.y,this}add(t){return this.x+=t.x,this.y+=t.y,this}addScalar(t){return this.x+=t,this.y+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this}subScalar(t){return this.x-=t,this.y-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this}multiply(t){return this.x*=t.x,this.y*=t.y,this}multiplyScalar(t){return this.x*=t,this.y*=t,this}divide(t){return this.x/=t.x,this.y/=t.y,this}divideScalar(t){return this.multiplyScalar(1/t)}applyMatrix3(t){const e=this.x,n=this.y,r=t.elements;return this.x=r[0]*e+r[3]*n+r[6],this.y=r[1]*e+r[4]*n+r[7],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(t){return this.x*t.x+this.y*t.y}cross(t){return this.x*t.y-this.y*t.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(t){const e=Math.sqrt(this.lengthSq()*t.lengthSq());if(e===0)return Math.PI/2;const n=this.dot(t)/e;return Math.acos(ae(n,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){const e=this.x-t.x,n=this.y-t.y;return e*e+n*n}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this}equals(t){return t.x===this.x&&t.y===this.y}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this}rotateAround(t,e){const n=Math.cos(e),r=Math.sin(e),s=this.x-t.x,o=this.y-t.y;return this.x=s*n-o*r+t.x,this.y=s*r+o*n+t.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}}class Bt{constructor(t,e,n,r,s,o,a,l,c){Bt.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],t!==void 0&&this.set(t,e,n,r,s,o,a,l,c)}set(t,e,n,r,s,o,a,l,c){const h=this.elements;return h[0]=t,h[1]=r,h[2]=a,h[3]=e,h[4]=s,h[5]=l,h[6]=n,h[7]=o,h[8]=c,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(t){const e=this.elements,n=t.elements;return e[0]=n[0],e[1]=n[1],e[2]=n[2],e[3]=n[3],e[4]=n[4],e[5]=n[5],e[6]=n[6],e[7]=n[7],e[8]=n[8],this}extractBasis(t,e,n){return t.setFromMatrix3Column(this,0),e.setFromMatrix3Column(this,1),n.setFromMatrix3Column(this,2),this}setFromMatrix4(t){const e=t.elements;return this.set(e[0],e[4],e[8],e[1],e[5],e[9],e[2],e[6],e[10]),this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,e){const n=t.elements,r=e.elements,s=this.elements,o=n[0],a=n[3],l=n[6],c=n[1],h=n[4],u=n[7],d=n[2],m=n[5],_=n[8],M=r[0],p=r[3],f=r[6],y=r[1],g=r[4],E=r[7],P=r[2],w=r[5],b=r[8];return s[0]=o*M+a*y+l*P,s[3]=o*p+a*g+l*w,s[6]=o*f+a*E+l*b,s[1]=c*M+h*y+u*P,s[4]=c*p+h*g+u*w,s[7]=c*f+h*E+u*b,s[2]=d*M+m*y+_*P,s[5]=d*p+m*g+_*w,s[8]=d*f+m*E+_*b,this}multiplyScalar(t){const e=this.elements;return e[0]*=t,e[3]*=t,e[6]*=t,e[1]*=t,e[4]*=t,e[7]*=t,e[2]*=t,e[5]*=t,e[8]*=t,this}determinant(){const t=this.elements,e=t[0],n=t[1],r=t[2],s=t[3],o=t[4],a=t[5],l=t[6],c=t[7],h=t[8];return e*o*h-e*a*c-n*s*h+n*a*l+r*s*c-r*o*l}invert(){const t=this.elements,e=t[0],n=t[1],r=t[2],s=t[3],o=t[4],a=t[5],l=t[6],c=t[7],h=t[8],u=h*o-a*c,d=a*l-h*s,m=c*s-o*l,_=e*u+n*d+r*m;if(_===0)return this.set(0,0,0,0,0,0,0,0,0);const M=1/_;return t[0]=u*M,t[1]=(r*c-h*n)*M,t[2]=(a*n-r*o)*M,t[3]=d*M,t[4]=(h*e-r*l)*M,t[5]=(r*s-a*e)*M,t[6]=m*M,t[7]=(n*l-c*e)*M,t[8]=(o*e-n*s)*M,this}transpose(){let t;const e=this.elements;return t=e[1],e[1]=e[3],e[3]=t,t=e[2],e[2]=e[6],e[6]=t,t=e[5],e[5]=e[7],e[7]=t,this}getNormalMatrix(t){return this.setFromMatrix4(t).invert().transpose()}transposeIntoArray(t){const e=this.elements;return t[0]=e[0],t[1]=e[3],t[2]=e[6],t[3]=e[1],t[4]=e[4],t[5]=e[7],t[6]=e[2],t[7]=e[5],t[8]=e[8],this}setUvTransform(t,e,n,r,s,o,a){const l=Math.cos(s),c=Math.sin(s);return this.set(n*l,n*c,-n*(l*o+c*a)+o+t,-r*c,r*l,-r*(-c*o+l*a)+a+e,0,0,1),this}scale(t,e){return this.premultiply(Ur.makeScale(t,e)),this}rotate(t){return this.premultiply(Ur.makeRotation(-t)),this}translate(t,e){return this.premultiply(Ur.makeTranslation(t,e)),this}makeTranslation(t,e){return t.isVector2?this.set(1,0,t.x,0,1,t.y,0,0,1):this.set(1,0,t,0,1,e,0,0,1),this}makeRotation(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,-n,0,n,e,0,0,0,1),this}makeScale(t,e){return this.set(t,0,0,0,e,0,0,0,1),this}equals(t){const e=this.elements,n=t.elements;for(let r=0;r<9;r++)if(e[r]!==n[r])return!1;return!0}fromArray(t,e=0){for(let n=0;n<9;n++)this.elements[n]=t[n+e];return this}toArray(t=[],e=0){const n=this.elements;return t[e]=n[0],t[e+1]=n[1],t[e+2]=n[2],t[e+3]=n[3],t[e+4]=n[4],t[e+5]=n[5],t[e+6]=n[6],t[e+7]=n[7],t[e+8]=n[8],t}clone(){return new this.constructor().fromArray(this.elements)}}const Ur=new Bt;function Vo(i){for(let t=i.length-1;t>=0;--t)if(i[t]>=65535)return!0;return!1}function pr(i){return document.createElementNS("http://www.w3.org/1999/xhtml",i)}function Hc(){const i=pr("canvas");return i.style.display="block",i}const Ea={};function Vc(i){i in Ea||(Ea[i]=!0,console.warn(i))}const Ta=new Bt().set(.8224621,.177538,0,.0331941,.9668058,0,.0170827,.0723974,.9105199),Aa=new Bt().set(1.2249401,-.2249404,0,-.0420569,1.0420571,0,-.0196376,-.0786361,1.0982735),Ii={[mn]:{transfer:cr,primaries:hr,toReference:i=>i,fromReference:i=>i},[ze]:{transfer:$t,primaries:hr,toReference:i=>i.convertSRGBToLinear(),fromReference:i=>i.convertLinearToSRGB()},[gr]:{transfer:cr,primaries:ur,toReference:i=>i.applyMatrix3(Aa),fromReference:i=>i.applyMatrix3(Ta)},[As]:{transfer:$t,primaries:ur,toReference:i=>i.convertSRGBToLinear().applyMatrix3(Aa),fromReference:i=>i.applyMatrix3(Ta).convertLinearToSRGB()}},kc=new Set([mn,gr]),Yt={enabled:!0,_workingColorSpace:mn,get workingColorSpace(){return this._workingColorSpace},set workingColorSpace(i){if(!kc.has(i))throw new Error(`Unsupported working color space, "${i}".`);this._workingColorSpace=i},convert:function(i,t,e){if(this.enabled===!1||t===e||!t||!e)return i;const n=Ii[t].toReference,r=Ii[e].fromReference;return r(n(i))},fromWorkingColorSpace:function(i,t){return this.convert(i,this._workingColorSpace,t)},toWorkingColorSpace:function(i,t){return this.convert(i,t,this._workingColorSpace)},getPrimaries:function(i){return Ii[i].primaries},getTransfer:function(i){return i===ln?cr:Ii[i].transfer}};function ii(i){return i<.04045?i*.0773993808:Math.pow(i*.9478672986+.0521327014,2.4)}function Ir(i){return i<.0031308?i*12.92:1.055*Math.pow(i,.41666)-.055}let Fn;class ko{static getDataURL(t){if(/^data:/i.test(t.src)||typeof HTMLCanvasElement>"u")return t.src;let e;if(t instanceof HTMLCanvasElement)e=t;else{Fn===void 0&&(Fn=pr("canvas")),Fn.width=t.width,Fn.height=t.height;const n=Fn.getContext("2d");t instanceof ImageData?n.putImageData(t,0,0):n.drawImage(t,0,0,t.width,t.height),e=Fn}return e.width>2048||e.height>2048?(console.warn("THREE.ImageUtils.getDataURL: Image converted to jpg for performance reasons",t),e.toDataURL("image/jpeg",.6)):e.toDataURL("image/png")}static sRGBToLinear(t){if(typeof HTMLImageElement<"u"&&t instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&t instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&t instanceof ImageBitmap){const e=pr("canvas");e.width=t.width,e.height=t.height;const n=e.getContext("2d");n.drawImage(t,0,0,t.width,t.height);const r=n.getImageData(0,0,t.width,t.height),s=r.data;for(let o=0;o<s.length;o++)s[o]=ii(s[o]/255)*255;return n.putImageData(r,0,0),e}else if(t.data){const e=t.data.slice(0);for(let n=0;n<e.length;n++)e instanceof Uint8Array||e instanceof Uint8ClampedArray?e[n]=Math.floor(ii(e[n]/255)*255):e[n]=ii(e[n]);return{data:e,width:t.width,height:t.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),t}}let Wc=0;class Wo{constructor(t=null){this.isSource=!0,Object.defineProperty(this,"id",{value:Wc++}),this.uuid=Un(),this.data=t,this.dataReady=!0,this.version=0}set needsUpdate(t){t===!0&&this.version++}toJSON(t){const e=t===void 0||typeof t=="string";if(!e&&t.images[this.uuid]!==void 0)return t.images[this.uuid];const n={uuid:this.uuid,url:""},r=this.data;if(r!==null){let s;if(Array.isArray(r)){s=[];for(let o=0,a=r.length;o<a;o++)r[o].isDataTexture?s.push(Nr(r[o].image)):s.push(Nr(r[o]))}else s=Nr(r);n.url=s}return e||(t.images[this.uuid]=n),n}}function Nr(i){return typeof HTMLImageElement<"u"&&i instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&i instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&i instanceof ImageBitmap?ko.getDataURL(i):i.data?{data:Array.from(i.data),width:i.width,height:i.height,type:i.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}let Xc=0;class ve extends li{constructor(t=ve.DEFAULT_IMAGE,e=ve.DEFAULT_MAPPING,n=Ne,r=Ne,s=ye,o=Rn,a=Fe,l=fn,c=ve.DEFAULT_ANISOTROPY,h=ln){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:Xc++}),this.uuid=Un(),this.name="",this.source=new Wo(t),this.mipmaps=[],this.mapping=e,this.channel=0,this.wrapS=n,this.wrapT=r,this.magFilter=s,this.minFilter=o,this.anisotropy=c,this.format=a,this.internalFormat=null,this.type=l,this.offset=new it(0,0),this.repeat=new it(1,1),this.center=new it(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new Bt,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=h,this.userData={},this.version=0,this.onUpdate=null,this.isRenderTargetTexture=!1,this.needsPMREMUpdate=!1}get image(){return this.source.data}set image(t=null){this.source.data=t}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}clone(){return new this.constructor().copy(this)}copy(t){return this.name=t.name,this.source=t.source,this.mipmaps=t.mipmaps.slice(0),this.mapping=t.mapping,this.channel=t.channel,this.wrapS=t.wrapS,this.wrapT=t.wrapT,this.magFilter=t.magFilter,this.minFilter=t.minFilter,this.anisotropy=t.anisotropy,this.format=t.format,this.internalFormat=t.internalFormat,this.type=t.type,this.offset.copy(t.offset),this.repeat.copy(t.repeat),this.center.copy(t.center),this.rotation=t.rotation,this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrix.copy(t.matrix),this.generateMipmaps=t.generateMipmaps,this.premultiplyAlpha=t.premultiplyAlpha,this.flipY=t.flipY,this.unpackAlignment=t.unpackAlignment,this.colorSpace=t.colorSpace,this.userData=JSON.parse(JSON.stringify(t.userData)),this.needsUpdate=!0,this}toJSON(t){const e=t===void 0||typeof t=="string";if(!e&&t.textures[this.uuid]!==void 0)return t.textures[this.uuid];const n={metadata:{version:4.6,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(t).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(n.userData=this.userData),e||(t.textures[this.uuid]=n),n}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(t){if(this.mapping!==Lo)return t;if(t.applyMatrix3(this.matrix),t.x<0||t.x>1)switch(this.wrapS){case ps:t.x=t.x-Math.floor(t.x);break;case Ne:t.x=t.x<0?0:1;break;case ms:Math.abs(Math.floor(t.x)%2)===1?t.x=Math.ceil(t.x)-t.x:t.x=t.x-Math.floor(t.x);break}if(t.y<0||t.y>1)switch(this.wrapT){case ps:t.y=t.y-Math.floor(t.y);break;case Ne:t.y=t.y<0?0:1;break;case ms:Math.abs(Math.floor(t.y)%2)===1?t.y=Math.ceil(t.y)-t.y:t.y=t.y-Math.floor(t.y);break}return this.flipY&&(t.y=1-t.y),t}set needsUpdate(t){t===!0&&(this.version++,this.source.needsUpdate=!0)}}ve.DEFAULT_IMAGE=null;ve.DEFAULT_MAPPING=Lo;ve.DEFAULT_ANISOTROPY=1;class te{constructor(t=0,e=0,n=0,r=1){te.prototype.isVector4=!0,this.x=t,this.y=e,this.z=n,this.w=r}get width(){return this.z}set width(t){this.z=t}get height(){return this.w}set height(t){this.w=t}set(t,e,n,r){return this.x=t,this.y=e,this.z=n,this.w=r,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this.w=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setW(t){return this.w=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;case 2:this.z=e;break;case 3:this.w=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this.w=t.w!==void 0?t.w:1,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this.w+=t.w,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this.w+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this.z=t.z+e.z,this.w=t.w+e.w,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this.z+=t.z*e,this.w+=t.w*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this.w-=t.w,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this.w-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this.z=t.z-e.z,this.w=t.w-e.w,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this.w*=t.w,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this.w*=t,this}applyMatrix4(t){const e=this.x,n=this.y,r=this.z,s=this.w,o=t.elements;return this.x=o[0]*e+o[4]*n+o[8]*r+o[12]*s,this.y=o[1]*e+o[5]*n+o[9]*r+o[13]*s,this.z=o[2]*e+o[6]*n+o[10]*r+o[14]*s,this.w=o[3]*e+o[7]*n+o[11]*r+o[15]*s,this}divideScalar(t){return this.multiplyScalar(1/t)}setAxisAngleFromQuaternion(t){this.w=2*Math.acos(t.w);const e=Math.sqrt(1-t.w*t.w);return e<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=t.x/e,this.y=t.y/e,this.z=t.z/e),this}setAxisAngleFromRotationMatrix(t){let e,n,r,s;const l=t.elements,c=l[0],h=l[4],u=l[8],d=l[1],m=l[5],_=l[9],M=l[2],p=l[6],f=l[10];if(Math.abs(h-d)<.01&&Math.abs(u-M)<.01&&Math.abs(_-p)<.01){if(Math.abs(h+d)<.1&&Math.abs(u+M)<.1&&Math.abs(_+p)<.1&&Math.abs(c+m+f-3)<.1)return this.set(1,0,0,0),this;e=Math.PI;const g=(c+1)/2,E=(m+1)/2,P=(f+1)/2,w=(h+d)/4,b=(u+M)/4,U=(_+p)/4;return g>E&&g>P?g<.01?(n=0,r=.707106781,s=.707106781):(n=Math.sqrt(g),r=w/n,s=b/n):E>P?E<.01?(n=.707106781,r=0,s=.707106781):(r=Math.sqrt(E),n=w/r,s=U/r):P<.01?(n=.707106781,r=.707106781,s=0):(s=Math.sqrt(P),n=b/s,r=U/s),this.set(n,r,s,e),this}let y=Math.sqrt((p-_)*(p-_)+(u-M)*(u-M)+(d-h)*(d-h));return Math.abs(y)<.001&&(y=1),this.x=(p-_)/y,this.y=(u-M)/y,this.z=(d-h)/y,this.w=Math.acos((c+m+f-1)/2),this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this.w=Math.min(this.w,t.w),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this.w=Math.max(this.w,t.w),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this.z=Math.max(t.z,Math.min(e.z,this.z)),this.w=Math.max(t.w,Math.min(e.w,this.w)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this.z=Math.max(t,Math.min(e,this.z)),this.w=Math.max(t,Math.min(e,this.w)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z+this.w*t.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this.z+=(t.z-this.z)*e,this.w+=(t.w-this.w)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this.z=t.z+(e.z-t.z)*n,this.w=t.w+(e.w-t.w)*n,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z&&t.w===this.w}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this.z=t[e+2],this.w=t[e+3],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t[e+2]=this.z,t[e+3]=this.w,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this.z=t.getZ(e),this.w=t.getW(e),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}}class qc extends li{constructor(t=1,e=1,n={}){super(),this.isRenderTarget=!0,this.width=t,this.height=e,this.depth=1,this.scissor=new te(0,0,t,e),this.scissorTest=!1,this.viewport=new te(0,0,t,e);const r={width:t,height:e,depth:1};n=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:ye,depthBuffer:!0,stencilBuffer:!1,depthTexture:null,samples:0,count:1},n);const s=new ve(r,n.mapping,n.wrapS,n.wrapT,n.magFilter,n.minFilter,n.format,n.type,n.anisotropy,n.colorSpace);s.flipY=!1,s.generateMipmaps=n.generateMipmaps,s.internalFormat=n.internalFormat,this.textures=[];const o=n.count;for(let a=0;a<o;a++)this.textures[a]=s.clone(),this.textures[a].isRenderTargetTexture=!0;this.depthBuffer=n.depthBuffer,this.stencilBuffer=n.stencilBuffer,this.depthTexture=n.depthTexture,this.samples=n.samples}get texture(){return this.textures[0]}set texture(t){this.textures[0]=t}setSize(t,e,n=1){if(this.width!==t||this.height!==e||this.depth!==n){this.width=t,this.height=e,this.depth=n;for(let r=0,s=this.textures.length;r<s;r++)this.textures[r].image.width=t,this.textures[r].image.height=e,this.textures[r].image.depth=n;this.dispose()}this.viewport.set(0,0,t,e),this.scissor.set(0,0,t,e)}clone(){return new this.constructor().copy(this)}copy(t){this.width=t.width,this.height=t.height,this.depth=t.depth,this.scissor.copy(t.scissor),this.scissorTest=t.scissorTest,this.viewport.copy(t.viewport),this.textures.length=0;for(let n=0,r=t.textures.length;n<r;n++)this.textures[n]=t.textures[n].clone(),this.textures[n].isRenderTargetTexture=!0;const e=Object.assign({},t.texture.image);return this.texture.source=new Wo(e),this.depthBuffer=t.depthBuffer,this.stencilBuffer=t.stencilBuffer,t.depthTexture!==null&&(this.depthTexture=t.depthTexture.clone()),this.samples=t.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}}class Ln extends qc{constructor(t=1,e=1,n={}){super(t,e,n),this.isWebGLRenderTarget=!0}}class Xo extends ve{constructor(t=null,e=1,n=1,r=1){super(null),this.isDataArrayTexture=!0,this.image={data:t,width:e,height:n,depth:r},this.magFilter=de,this.minFilter=de,this.wrapR=Ne,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class Yc extends ve{constructor(t=null,e=1,n=1,r=1){super(null),this.isData3DTexture=!0,this.image={data:t,width:e,height:n,depth:r},this.magFilter=de,this.minFilter=de,this.wrapR=Ne,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class Pi{constructor(t=0,e=0,n=0,r=1){this.isQuaternion=!0,this._x=t,this._y=e,this._z=n,this._w=r}static slerpFlat(t,e,n,r,s,o,a){let l=n[r+0],c=n[r+1],h=n[r+2],u=n[r+3];const d=s[o+0],m=s[o+1],_=s[o+2],M=s[o+3];if(a===0){t[e+0]=l,t[e+1]=c,t[e+2]=h,t[e+3]=u;return}if(a===1){t[e+0]=d,t[e+1]=m,t[e+2]=_,t[e+3]=M;return}if(u!==M||l!==d||c!==m||h!==_){let p=1-a;const f=l*d+c*m+h*_+u*M,y=f>=0?1:-1,g=1-f*f;if(g>Number.EPSILON){const P=Math.sqrt(g),w=Math.atan2(P,f*y);p=Math.sin(p*w)/P,a=Math.sin(a*w)/P}const E=a*y;if(l=l*p+d*E,c=c*p+m*E,h=h*p+_*E,u=u*p+M*E,p===1-a){const P=1/Math.sqrt(l*l+c*c+h*h+u*u);l*=P,c*=P,h*=P,u*=P}}t[e]=l,t[e+1]=c,t[e+2]=h,t[e+3]=u}static multiplyQuaternionsFlat(t,e,n,r,s,o){const a=n[r],l=n[r+1],c=n[r+2],h=n[r+3],u=s[o],d=s[o+1],m=s[o+2],_=s[o+3];return t[e]=a*_+h*u+l*m-c*d,t[e+1]=l*_+h*d+c*u-a*m,t[e+2]=c*_+h*m+a*d-l*u,t[e+3]=h*_-a*u-l*d-c*m,t}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get w(){return this._w}set w(t){this._w=t,this._onChangeCallback()}set(t,e,n,r){return this._x=t,this._y=e,this._z=n,this._w=r,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(t){return this._x=t.x,this._y=t.y,this._z=t.z,this._w=t.w,this._onChangeCallback(),this}setFromEuler(t,e=!0){const n=t._x,r=t._y,s=t._z,o=t._order,a=Math.cos,l=Math.sin,c=a(n/2),h=a(r/2),u=a(s/2),d=l(n/2),m=l(r/2),_=l(s/2);switch(o){case"XYZ":this._x=d*h*u+c*m*_,this._y=c*m*u-d*h*_,this._z=c*h*_+d*m*u,this._w=c*h*u-d*m*_;break;case"YXZ":this._x=d*h*u+c*m*_,this._y=c*m*u-d*h*_,this._z=c*h*_-d*m*u,this._w=c*h*u+d*m*_;break;case"ZXY":this._x=d*h*u-c*m*_,this._y=c*m*u+d*h*_,this._z=c*h*_+d*m*u,this._w=c*h*u-d*m*_;break;case"ZYX":this._x=d*h*u-c*m*_,this._y=c*m*u+d*h*_,this._z=c*h*_-d*m*u,this._w=c*h*u+d*m*_;break;case"YZX":this._x=d*h*u+c*m*_,this._y=c*m*u+d*h*_,this._z=c*h*_-d*m*u,this._w=c*h*u-d*m*_;break;case"XZY":this._x=d*h*u-c*m*_,this._y=c*m*u-d*h*_,this._z=c*h*_+d*m*u,this._w=c*h*u+d*m*_;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+o)}return e===!0&&this._onChangeCallback(),this}setFromAxisAngle(t,e){const n=e/2,r=Math.sin(n);return this._x=t.x*r,this._y=t.y*r,this._z=t.z*r,this._w=Math.cos(n),this._onChangeCallback(),this}setFromRotationMatrix(t){const e=t.elements,n=e[0],r=e[4],s=e[8],o=e[1],a=e[5],l=e[9],c=e[2],h=e[6],u=e[10],d=n+a+u;if(d>0){const m=.5/Math.sqrt(d+1);this._w=.25/m,this._x=(h-l)*m,this._y=(s-c)*m,this._z=(o-r)*m}else if(n>a&&n>u){const m=2*Math.sqrt(1+n-a-u);this._w=(h-l)/m,this._x=.25*m,this._y=(r+o)/m,this._z=(s+c)/m}else if(a>u){const m=2*Math.sqrt(1+a-n-u);this._w=(s-c)/m,this._x=(r+o)/m,this._y=.25*m,this._z=(l+h)/m}else{const m=2*Math.sqrt(1+u-n-a);this._w=(o-r)/m,this._x=(s+c)/m,this._y=(l+h)/m,this._z=.25*m}return this._onChangeCallback(),this}setFromUnitVectors(t,e){let n=t.dot(e)+1;return n<Number.EPSILON?(n=0,Math.abs(t.x)>Math.abs(t.z)?(this._x=-t.y,this._y=t.x,this._z=0,this._w=n):(this._x=0,this._y=-t.z,this._z=t.y,this._w=n)):(this._x=t.y*e.z-t.z*e.y,this._y=t.z*e.x-t.x*e.z,this._z=t.x*e.y-t.y*e.x,this._w=n),this.normalize()}angleTo(t){return 2*Math.acos(Math.abs(ae(this.dot(t),-1,1)))}rotateTowards(t,e){const n=this.angleTo(t);if(n===0)return this;const r=Math.min(1,e/n);return this.slerp(t,r),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(t){return this._x*t._x+this._y*t._y+this._z*t._z+this._w*t._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let t=this.length();return t===0?(this._x=0,this._y=0,this._z=0,this._w=1):(t=1/t,this._x=this._x*t,this._y=this._y*t,this._z=this._z*t,this._w=this._w*t),this._onChangeCallback(),this}multiply(t){return this.multiplyQuaternions(this,t)}premultiply(t){return this.multiplyQuaternions(t,this)}multiplyQuaternions(t,e){const n=t._x,r=t._y,s=t._z,o=t._w,a=e._x,l=e._y,c=e._z,h=e._w;return this._x=n*h+o*a+r*c-s*l,this._y=r*h+o*l+s*a-n*c,this._z=s*h+o*c+n*l-r*a,this._w=o*h-n*a-r*l-s*c,this._onChangeCallback(),this}slerp(t,e){if(e===0)return this;if(e===1)return this.copy(t);const n=this._x,r=this._y,s=this._z,o=this._w;let a=o*t._w+n*t._x+r*t._y+s*t._z;if(a<0?(this._w=-t._w,this._x=-t._x,this._y=-t._y,this._z=-t._z,a=-a):this.copy(t),a>=1)return this._w=o,this._x=n,this._y=r,this._z=s,this;const l=1-a*a;if(l<=Number.EPSILON){const m=1-e;return this._w=m*o+e*this._w,this._x=m*n+e*this._x,this._y=m*r+e*this._y,this._z=m*s+e*this._z,this.normalize(),this}const c=Math.sqrt(l),h=Math.atan2(c,a),u=Math.sin((1-e)*h)/c,d=Math.sin(e*h)/c;return this._w=o*u+this._w*d,this._x=n*u+this._x*d,this._y=r*u+this._y*d,this._z=s*u+this._z*d,this._onChangeCallback(),this}slerpQuaternions(t,e,n){return this.copy(t).slerp(e,n)}random(){const t=2*Math.PI*Math.random(),e=2*Math.PI*Math.random(),n=Math.random(),r=Math.sqrt(1-n),s=Math.sqrt(n);return this.set(r*Math.sin(t),r*Math.cos(t),s*Math.sin(e),s*Math.cos(e))}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._w===this._w}fromArray(t,e=0){return this._x=t[e],this._y=t[e+1],this._z=t[e+2],this._w=t[e+3],this._onChangeCallback(),this}toArray(t=[],e=0){return t[e]=this._x,t[e+1]=this._y,t[e+2]=this._z,t[e+3]=this._w,t}fromBufferAttribute(t,e){return this._x=t.getX(e),this._y=t.getY(e),this._z=t.getZ(e),this._w=t.getW(e),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}}class C{constructor(t=0,e=0,n=0){C.prototype.isVector3=!0,this.x=t,this.y=e,this.z=n}set(t,e,n){return n===void 0&&(n=this.z),this.x=t,this.y=e,this.z=n,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;case 2:this.z=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this.z=t.z+e.z,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this.z+=t.z*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this.z=t.z-e.z,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this}multiplyVectors(t,e){return this.x=t.x*e.x,this.y=t.y*e.y,this.z=t.z*e.z,this}applyEuler(t){return this.applyQuaternion(ba.setFromEuler(t))}applyAxisAngle(t,e){return this.applyQuaternion(ba.setFromAxisAngle(t,e))}applyMatrix3(t){const e=this.x,n=this.y,r=this.z,s=t.elements;return this.x=s[0]*e+s[3]*n+s[6]*r,this.y=s[1]*e+s[4]*n+s[7]*r,this.z=s[2]*e+s[5]*n+s[8]*r,this}applyNormalMatrix(t){return this.applyMatrix3(t).normalize()}applyMatrix4(t){const e=this.x,n=this.y,r=this.z,s=t.elements,o=1/(s[3]*e+s[7]*n+s[11]*r+s[15]);return this.x=(s[0]*e+s[4]*n+s[8]*r+s[12])*o,this.y=(s[1]*e+s[5]*n+s[9]*r+s[13])*o,this.z=(s[2]*e+s[6]*n+s[10]*r+s[14])*o,this}applyQuaternion(t){const e=this.x,n=this.y,r=this.z,s=t.x,o=t.y,a=t.z,l=t.w,c=2*(o*r-a*n),h=2*(a*e-s*r),u=2*(s*n-o*e);return this.x=e+l*c+o*u-a*h,this.y=n+l*h+a*c-s*u,this.z=r+l*u+s*h-o*c,this}project(t){return this.applyMatrix4(t.matrixWorldInverse).applyMatrix4(t.projectionMatrix)}unproject(t){return this.applyMatrix4(t.projectionMatrixInverse).applyMatrix4(t.matrixWorld)}transformDirection(t){const e=this.x,n=this.y,r=this.z,s=t.elements;return this.x=s[0]*e+s[4]*n+s[8]*r,this.y=s[1]*e+s[5]*n+s[9]*r,this.z=s[2]*e+s[6]*n+s[10]*r,this.normalize()}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this}divideScalar(t){return this.multiplyScalar(1/t)}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this.z=Math.max(t.z,Math.min(e.z,this.z)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this.z=Math.max(t,Math.min(e,this.z)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this.z+=(t.z-this.z)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this.z=t.z+(e.z-t.z)*n,this}cross(t){return this.crossVectors(this,t)}crossVectors(t,e){const n=t.x,r=t.y,s=t.z,o=e.x,a=e.y,l=e.z;return this.x=r*l-s*a,this.y=s*o-n*l,this.z=n*a-r*o,this}projectOnVector(t){const e=t.lengthSq();if(e===0)return this.set(0,0,0);const n=t.dot(this)/e;return this.copy(t).multiplyScalar(n)}projectOnPlane(t){return Fr.copy(this).projectOnVector(t),this.sub(Fr)}reflect(t){return this.sub(Fr.copy(t).multiplyScalar(2*this.dot(t)))}angleTo(t){const e=Math.sqrt(this.lengthSq()*t.lengthSq());if(e===0)return Math.PI/2;const n=this.dot(t)/e;return Math.acos(ae(n,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){const e=this.x-t.x,n=this.y-t.y,r=this.z-t.z;return e*e+n*n+r*r}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)+Math.abs(this.z-t.z)}setFromSpherical(t){return this.setFromSphericalCoords(t.radius,t.phi,t.theta)}setFromSphericalCoords(t,e,n){const r=Math.sin(e)*t;return this.x=r*Math.sin(n),this.y=Math.cos(e)*t,this.z=r*Math.cos(n),this}setFromCylindrical(t){return this.setFromCylindricalCoords(t.radius,t.theta,t.y)}setFromCylindricalCoords(t,e,n){return this.x=t*Math.sin(e),this.y=n,this.z=t*Math.cos(e),this}setFromMatrixPosition(t){const e=t.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this}setFromMatrixScale(t){const e=this.setFromMatrixColumn(t,0).length(),n=this.setFromMatrixColumn(t,1).length(),r=this.setFromMatrixColumn(t,2).length();return this.x=e,this.y=n,this.z=r,this}setFromMatrixColumn(t,e){return this.fromArray(t.elements,e*4)}setFromMatrix3Column(t,e){return this.fromArray(t.elements,e*3)}setFromEuler(t){return this.x=t._x,this.y=t._y,this.z=t._z,this}setFromColor(t){return this.x=t.r,this.y=t.g,this.z=t.b,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this.z=t[e+2],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t[e+2]=this.z,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this.z=t.getZ(e),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){const t=Math.random()*Math.PI*2,e=Math.random()*2-1,n=Math.sqrt(1-e*e);return this.x=n*Math.cos(t),this.y=e,this.z=n*Math.sin(t),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}}const Fr=new C,ba=new Pi;class In{constructor(t=new C(1/0,1/0,1/0),e=new C(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=t,this.max=e}set(t,e){return this.min.copy(t),this.max.copy(e),this}setFromArray(t){this.makeEmpty();for(let e=0,n=t.length;e<n;e+=3)this.expandByPoint(De.fromArray(t,e));return this}setFromBufferAttribute(t){this.makeEmpty();for(let e=0,n=t.count;e<n;e++)this.expandByPoint(De.fromBufferAttribute(t,e));return this}setFromPoints(t){this.makeEmpty();for(let e=0,n=t.length;e<n;e++)this.expandByPoint(t[e]);return this}setFromCenterAndSize(t,e){const n=De.copy(e).multiplyScalar(.5);return this.min.copy(t).sub(n),this.max.copy(t).add(n),this}setFromObject(t,e=!1){return this.makeEmpty(),this.expandByObject(t,e)}clone(){return new this.constructor().copy(this)}copy(t){return this.min.copy(t.min),this.max.copy(t.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(t){return this.isEmpty()?t.set(0,0,0):t.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(t){return this.isEmpty()?t.set(0,0,0):t.subVectors(this.max,this.min)}expandByPoint(t){return this.min.min(t),this.max.max(t),this}expandByVector(t){return this.min.sub(t),this.max.add(t),this}expandByScalar(t){return this.min.addScalar(-t),this.max.addScalar(t),this}expandByObject(t,e=!1){t.updateWorldMatrix(!1,!1);const n=t.geometry;if(n!==void 0){const s=n.getAttribute("position");if(e===!0&&s!==void 0&&t.isInstancedMesh!==!0)for(let o=0,a=s.count;o<a;o++)t.isMesh===!0?t.getVertexPosition(o,De):De.fromBufferAttribute(s,o),De.applyMatrix4(t.matrixWorld),this.expandByPoint(De);else t.boundingBox!==void 0?(t.boundingBox===null&&t.computeBoundingBox(),Ni.copy(t.boundingBox)):(n.boundingBox===null&&n.computeBoundingBox(),Ni.copy(n.boundingBox)),Ni.applyMatrix4(t.matrixWorld),this.union(Ni)}const r=t.children;for(let s=0,o=r.length;s<o;s++)this.expandByObject(r[s],e);return this}containsPoint(t){return!(t.x<this.min.x||t.x>this.max.x||t.y<this.min.y||t.y>this.max.y||t.z<this.min.z||t.z>this.max.z)}containsBox(t){return this.min.x<=t.min.x&&t.max.x<=this.max.x&&this.min.y<=t.min.y&&t.max.y<=this.max.y&&this.min.z<=t.min.z&&t.max.z<=this.max.z}getParameter(t,e){return e.set((t.x-this.min.x)/(this.max.x-this.min.x),(t.y-this.min.y)/(this.max.y-this.min.y),(t.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(t){return!(t.max.x<this.min.x||t.min.x>this.max.x||t.max.y<this.min.y||t.min.y>this.max.y||t.max.z<this.min.z||t.min.z>this.max.z)}intersectsSphere(t){return this.clampPoint(t.center,De),De.distanceToSquared(t.center)<=t.radius*t.radius}intersectsPlane(t){let e,n;return t.normal.x>0?(e=t.normal.x*this.min.x,n=t.normal.x*this.max.x):(e=t.normal.x*this.max.x,n=t.normal.x*this.min.x),t.normal.y>0?(e+=t.normal.y*this.min.y,n+=t.normal.y*this.max.y):(e+=t.normal.y*this.max.y,n+=t.normal.y*this.min.y),t.normal.z>0?(e+=t.normal.z*this.min.z,n+=t.normal.z*this.max.z):(e+=t.normal.z*this.max.z,n+=t.normal.z*this.min.z),e<=-t.constant&&n>=-t.constant}intersectsTriangle(t){if(this.isEmpty())return!1;this.getCenter(pi),Fi.subVectors(this.max,pi),On.subVectors(t.a,pi),Bn.subVectors(t.b,pi),zn.subVectors(t.c,pi),en.subVectors(Bn,On),nn.subVectors(zn,Bn),vn.subVectors(On,zn);let e=[0,-en.z,en.y,0,-nn.z,nn.y,0,-vn.z,vn.y,en.z,0,-en.x,nn.z,0,-nn.x,vn.z,0,-vn.x,-en.y,en.x,0,-nn.y,nn.x,0,-vn.y,vn.x,0];return!Or(e,On,Bn,zn,Fi)||(e=[1,0,0,0,1,0,0,0,1],!Or(e,On,Bn,zn,Fi))?!1:(Oi.crossVectors(en,nn),e=[Oi.x,Oi.y,Oi.z],Or(e,On,Bn,zn,Fi))}clampPoint(t,e){return e.copy(t).clamp(this.min,this.max)}distanceToPoint(t){return this.clampPoint(t,De).distanceTo(t)}getBoundingSphere(t){return this.isEmpty()?t.makeEmpty():(this.getCenter(t.center),t.radius=this.getSize(De).length()*.5),t}intersect(t){return this.min.max(t.min),this.max.min(t.max),this.isEmpty()&&this.makeEmpty(),this}union(t){return this.min.min(t.min),this.max.max(t.max),this}applyMatrix4(t){return this.isEmpty()?this:(qe[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(t),qe[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(t),qe[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(t),qe[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(t),qe[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(t),qe[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(t),qe[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(t),qe[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(t),this.setFromPoints(qe),this)}translate(t){return this.min.add(t),this.max.add(t),this}equals(t){return t.min.equals(this.min)&&t.max.equals(this.max)}}const qe=[new C,new C,new C,new C,new C,new C,new C,new C],De=new C,Ni=new In,On=new C,Bn=new C,zn=new C,en=new C,nn=new C,vn=new C,pi=new C,Fi=new C,Oi=new C,xn=new C;function Or(i,t,e,n,r){for(let s=0,o=i.length-3;s<=o;s+=3){xn.fromArray(i,s);const a=r.x*Math.abs(xn.x)+r.y*Math.abs(xn.y)+r.z*Math.abs(xn.z),l=t.dot(xn),c=e.dot(xn),h=n.dot(xn);if(Math.max(-Math.max(l,c,h),Math.min(l,c,h))>a)return!1}return!0}const Jc=new In,mi=new C,Br=new C;class ci{constructor(t=new C,e=-1){this.isSphere=!0,this.center=t,this.radius=e}set(t,e){return this.center.copy(t),this.radius=e,this}setFromPoints(t,e){const n=this.center;e!==void 0?n.copy(e):Jc.setFromPoints(t).getCenter(n);let r=0;for(let s=0,o=t.length;s<o;s++)r=Math.max(r,n.distanceToSquared(t[s]));return this.radius=Math.sqrt(r),this}copy(t){return this.center.copy(t.center),this.radius=t.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(t){return t.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(t){return t.distanceTo(this.center)-this.radius}intersectsSphere(t){const e=this.radius+t.radius;return t.center.distanceToSquared(this.center)<=e*e}intersectsBox(t){return t.intersectsSphere(this)}intersectsPlane(t){return Math.abs(t.distanceToPoint(this.center))<=this.radius}clampPoint(t,e){const n=this.center.distanceToSquared(t);return e.copy(t),n>this.radius*this.radius&&(e.sub(this.center).normalize(),e.multiplyScalar(this.radius).add(this.center)),e}getBoundingBox(t){return this.isEmpty()?(t.makeEmpty(),t):(t.set(this.center,this.center),t.expandByScalar(this.radius),t)}applyMatrix4(t){return this.center.applyMatrix4(t),this.radius=this.radius*t.getMaxScaleOnAxis(),this}translate(t){return this.center.add(t),this}expandByPoint(t){if(this.isEmpty())return this.center.copy(t),this.radius=0,this;mi.subVectors(t,this.center);const e=mi.lengthSq();if(e>this.radius*this.radius){const n=Math.sqrt(e),r=(n-this.radius)*.5;this.center.addScaledVector(mi,r/n),this.radius+=r}return this}union(t){return t.isEmpty()?this:this.isEmpty()?(this.copy(t),this):(this.center.equals(t.center)===!0?this.radius=Math.max(this.radius,t.radius):(Br.subVectors(t.center,this.center).setLength(t.radius),this.expandByPoint(mi.copy(t.center).add(Br)),this.expandByPoint(mi.copy(t.center).sub(Br))),this)}equals(t){return t.center.equals(this.center)&&t.radius===this.radius}clone(){return new this.constructor().copy(this)}}const Ye=new C,zr=new C,Bi=new C,rn=new C,Gr=new C,zi=new C,Hr=new C;class ws{constructor(t=new C,e=new C(0,0,-1)){this.origin=t,this.direction=e}set(t,e){return this.origin.copy(t),this.direction.copy(e),this}copy(t){return this.origin.copy(t.origin),this.direction.copy(t.direction),this}at(t,e){return e.copy(this.origin).addScaledVector(this.direction,t)}lookAt(t){return this.direction.copy(t).sub(this.origin).normalize(),this}recast(t){return this.origin.copy(this.at(t,Ye)),this}closestPointToPoint(t,e){e.subVectors(t,this.origin);const n=e.dot(this.direction);return n<0?e.copy(this.origin):e.copy(this.origin).addScaledVector(this.direction,n)}distanceToPoint(t){return Math.sqrt(this.distanceSqToPoint(t))}distanceSqToPoint(t){const e=Ye.subVectors(t,this.origin).dot(this.direction);return e<0?this.origin.distanceToSquared(t):(Ye.copy(this.origin).addScaledVector(this.direction,e),Ye.distanceToSquared(t))}distanceSqToSegment(t,e,n,r){zr.copy(t).add(e).multiplyScalar(.5),Bi.copy(e).sub(t).normalize(),rn.copy(this.origin).sub(zr);const s=t.distanceTo(e)*.5,o=-this.direction.dot(Bi),a=rn.dot(this.direction),l=-rn.dot(Bi),c=rn.lengthSq(),h=Math.abs(1-o*o);let u,d,m,_;if(h>0)if(u=o*l-a,d=o*a-l,_=s*h,u>=0)if(d>=-_)if(d<=_){const M=1/h;u*=M,d*=M,m=u*(u+o*d+2*a)+d*(o*u+d+2*l)+c}else d=s,u=Math.max(0,-(o*d+a)),m=-u*u+d*(d+2*l)+c;else d=-s,u=Math.max(0,-(o*d+a)),m=-u*u+d*(d+2*l)+c;else d<=-_?(u=Math.max(0,-(-o*s+a)),d=u>0?-s:Math.min(Math.max(-s,-l),s),m=-u*u+d*(d+2*l)+c):d<=_?(u=0,d=Math.min(Math.max(-s,-l),s),m=d*(d+2*l)+c):(u=Math.max(0,-(o*s+a)),d=u>0?s:Math.min(Math.max(-s,-l),s),m=-u*u+d*(d+2*l)+c);else d=o>0?-s:s,u=Math.max(0,-(o*d+a)),m=-u*u+d*(d+2*l)+c;return n&&n.copy(this.origin).addScaledVector(this.direction,u),r&&r.copy(zr).addScaledVector(Bi,d),m}intersectSphere(t,e){Ye.subVectors(t.center,this.origin);const n=Ye.dot(this.direction),r=Ye.dot(Ye)-n*n,s=t.radius*t.radius;if(r>s)return null;const o=Math.sqrt(s-r),a=n-o,l=n+o;return l<0?null:a<0?this.at(l,e):this.at(a,e)}intersectsSphere(t){return this.distanceSqToPoint(t.center)<=t.radius*t.radius}distanceToPlane(t){const e=t.normal.dot(this.direction);if(e===0)return t.distanceToPoint(this.origin)===0?0:null;const n=-(this.origin.dot(t.normal)+t.constant)/e;return n>=0?n:null}intersectPlane(t,e){const n=this.distanceToPlane(t);return n===null?null:this.at(n,e)}intersectsPlane(t){const e=t.distanceToPoint(this.origin);return e===0||t.normal.dot(this.direction)*e<0}intersectBox(t,e){let n,r,s,o,a,l;const c=1/this.direction.x,h=1/this.direction.y,u=1/this.direction.z,d=this.origin;return c>=0?(n=(t.min.x-d.x)*c,r=(t.max.x-d.x)*c):(n=(t.max.x-d.x)*c,r=(t.min.x-d.x)*c),h>=0?(s=(t.min.y-d.y)*h,o=(t.max.y-d.y)*h):(s=(t.max.y-d.y)*h,o=(t.min.y-d.y)*h),n>o||s>r||((s>n||isNaN(n))&&(n=s),(o<r||isNaN(r))&&(r=o),u>=0?(a=(t.min.z-d.z)*u,l=(t.max.z-d.z)*u):(a=(t.max.z-d.z)*u,l=(t.min.z-d.z)*u),n>l||a>r)||((a>n||n!==n)&&(n=a),(l<r||r!==r)&&(r=l),r<0)?null:this.at(n>=0?n:r,e)}intersectsBox(t){return this.intersectBox(t,Ye)!==null}intersectTriangle(t,e,n,r,s){Gr.subVectors(e,t),zi.subVectors(n,t),Hr.crossVectors(Gr,zi);let o=this.direction.dot(Hr),a;if(o>0){if(r)return null;a=1}else if(o<0)a=-1,o=-o;else return null;rn.subVectors(this.origin,t);const l=a*this.direction.dot(zi.crossVectors(rn,zi));if(l<0)return null;const c=a*this.direction.dot(Gr.cross(rn));if(c<0||l+c>o)return null;const h=-a*rn.dot(Hr);return h<0?null:this.at(h/o,s)}applyMatrix4(t){return this.origin.applyMatrix4(t),this.direction.transformDirection(t),this}equals(t){return t.origin.equals(this.origin)&&t.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}}class Jt{constructor(t,e,n,r,s,o,a,l,c,h,u,d,m,_,M,p){Jt.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],t!==void 0&&this.set(t,e,n,r,s,o,a,l,c,h,u,d,m,_,M,p)}set(t,e,n,r,s,o,a,l,c,h,u,d,m,_,M,p){const f=this.elements;return f[0]=t,f[4]=e,f[8]=n,f[12]=r,f[1]=s,f[5]=o,f[9]=a,f[13]=l,f[2]=c,f[6]=h,f[10]=u,f[14]=d,f[3]=m,f[7]=_,f[11]=M,f[15]=p,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new Jt().fromArray(this.elements)}copy(t){const e=this.elements,n=t.elements;return e[0]=n[0],e[1]=n[1],e[2]=n[2],e[3]=n[3],e[4]=n[4],e[5]=n[5],e[6]=n[6],e[7]=n[7],e[8]=n[8],e[9]=n[9],e[10]=n[10],e[11]=n[11],e[12]=n[12],e[13]=n[13],e[14]=n[14],e[15]=n[15],this}copyPosition(t){const e=this.elements,n=t.elements;return e[12]=n[12],e[13]=n[13],e[14]=n[14],this}setFromMatrix3(t){const e=t.elements;return this.set(e[0],e[3],e[6],0,e[1],e[4],e[7],0,e[2],e[5],e[8],0,0,0,0,1),this}extractBasis(t,e,n){return t.setFromMatrixColumn(this,0),e.setFromMatrixColumn(this,1),n.setFromMatrixColumn(this,2),this}makeBasis(t,e,n){return this.set(t.x,e.x,n.x,0,t.y,e.y,n.y,0,t.z,e.z,n.z,0,0,0,0,1),this}extractRotation(t){const e=this.elements,n=t.elements,r=1/Gn.setFromMatrixColumn(t,0).length(),s=1/Gn.setFromMatrixColumn(t,1).length(),o=1/Gn.setFromMatrixColumn(t,2).length();return e[0]=n[0]*r,e[1]=n[1]*r,e[2]=n[2]*r,e[3]=0,e[4]=n[4]*s,e[5]=n[5]*s,e[6]=n[6]*s,e[7]=0,e[8]=n[8]*o,e[9]=n[9]*o,e[10]=n[10]*o,e[11]=0,e[12]=0,e[13]=0,e[14]=0,e[15]=1,this}makeRotationFromEuler(t){const e=this.elements,n=t.x,r=t.y,s=t.z,o=Math.cos(n),a=Math.sin(n),l=Math.cos(r),c=Math.sin(r),h=Math.cos(s),u=Math.sin(s);if(t.order==="XYZ"){const d=o*h,m=o*u,_=a*h,M=a*u;e[0]=l*h,e[4]=-l*u,e[8]=c,e[1]=m+_*c,e[5]=d-M*c,e[9]=-a*l,e[2]=M-d*c,e[6]=_+m*c,e[10]=o*l}else if(t.order==="YXZ"){const d=l*h,m=l*u,_=c*h,M=c*u;e[0]=d+M*a,e[4]=_*a-m,e[8]=o*c,e[1]=o*u,e[5]=o*h,e[9]=-a,e[2]=m*a-_,e[6]=M+d*a,e[10]=o*l}else if(t.order==="ZXY"){const d=l*h,m=l*u,_=c*h,M=c*u;e[0]=d-M*a,e[4]=-o*u,e[8]=_+m*a,e[1]=m+_*a,e[5]=o*h,e[9]=M-d*a,e[2]=-o*c,e[6]=a,e[10]=o*l}else if(t.order==="ZYX"){const d=o*h,m=o*u,_=a*h,M=a*u;e[0]=l*h,e[4]=_*c-m,e[8]=d*c+M,e[1]=l*u,e[5]=M*c+d,e[9]=m*c-_,e[2]=-c,e[6]=a*l,e[10]=o*l}else if(t.order==="YZX"){const d=o*l,m=o*c,_=a*l,M=a*c;e[0]=l*h,e[4]=M-d*u,e[8]=_*u+m,e[1]=u,e[5]=o*h,e[9]=-a*h,e[2]=-c*h,e[6]=m*u+_,e[10]=d-M*u}else if(t.order==="XZY"){const d=o*l,m=o*c,_=a*l,M=a*c;e[0]=l*h,e[4]=-u,e[8]=c*h,e[1]=d*u+M,e[5]=o*h,e[9]=m*u-_,e[2]=_*u-m,e[6]=a*h,e[10]=M*u+d}return e[3]=0,e[7]=0,e[11]=0,e[12]=0,e[13]=0,e[14]=0,e[15]=1,this}makeRotationFromQuaternion(t){return this.compose(Zc,t,Kc)}lookAt(t,e,n){const r=this.elements;return Ae.subVectors(t,e),Ae.lengthSq()===0&&(Ae.z=1),Ae.normalize(),sn.crossVectors(n,Ae),sn.lengthSq()===0&&(Math.abs(n.z)===1?Ae.x+=1e-4:Ae.z+=1e-4,Ae.normalize(),sn.crossVectors(n,Ae)),sn.normalize(),Gi.crossVectors(Ae,sn),r[0]=sn.x,r[4]=Gi.x,r[8]=Ae.x,r[1]=sn.y,r[5]=Gi.y,r[9]=Ae.y,r[2]=sn.z,r[6]=Gi.z,r[10]=Ae.z,this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,e){const n=t.elements,r=e.elements,s=this.elements,o=n[0],a=n[4],l=n[8],c=n[12],h=n[1],u=n[5],d=n[9],m=n[13],_=n[2],M=n[6],p=n[10],f=n[14],y=n[3],g=n[7],E=n[11],P=n[15],w=r[0],b=r[4],U=r[8],V=r[12],v=r[1],A=r[5],Z=r[9],K=r[13],L=r[2],k=r[6],z=r[10],J=r[14],X=r[3],q=r[7],nt=r[11],et=r[15];return s[0]=o*w+a*v+l*L+c*X,s[4]=o*b+a*A+l*k+c*q,s[8]=o*U+a*Z+l*z+c*nt,s[12]=o*V+a*K+l*J+c*et,s[1]=h*w+u*v+d*L+m*X,s[5]=h*b+u*A+d*k+m*q,s[9]=h*U+u*Z+d*z+m*nt,s[13]=h*V+u*K+d*J+m*et,s[2]=_*w+M*v+p*L+f*X,s[6]=_*b+M*A+p*k+f*q,s[10]=_*U+M*Z+p*z+f*nt,s[14]=_*V+M*K+p*J+f*et,s[3]=y*w+g*v+E*L+P*X,s[7]=y*b+g*A+E*k+P*q,s[11]=y*U+g*Z+E*z+P*nt,s[15]=y*V+g*K+E*J+P*et,this}multiplyScalar(t){const e=this.elements;return e[0]*=t,e[4]*=t,e[8]*=t,e[12]*=t,e[1]*=t,e[5]*=t,e[9]*=t,e[13]*=t,e[2]*=t,e[6]*=t,e[10]*=t,e[14]*=t,e[3]*=t,e[7]*=t,e[11]*=t,e[15]*=t,this}determinant(){const t=this.elements,e=t[0],n=t[4],r=t[8],s=t[12],o=t[1],a=t[5],l=t[9],c=t[13],h=t[2],u=t[6],d=t[10],m=t[14],_=t[3],M=t[7],p=t[11],f=t[15];return _*(+s*l*u-r*c*u-s*a*d+n*c*d+r*a*m-n*l*m)+M*(+e*l*m-e*c*d+s*o*d-r*o*m+r*c*h-s*l*h)+p*(+e*c*u-e*a*m-s*o*u+n*o*m+s*a*h-n*c*h)+f*(-r*a*h-e*l*u+e*a*d+r*o*u-n*o*d+n*l*h)}transpose(){const t=this.elements;let e;return e=t[1],t[1]=t[4],t[4]=e,e=t[2],t[2]=t[8],t[8]=e,e=t[6],t[6]=t[9],t[9]=e,e=t[3],t[3]=t[12],t[12]=e,e=t[7],t[7]=t[13],t[13]=e,e=t[11],t[11]=t[14],t[14]=e,this}setPosition(t,e,n){const r=this.elements;return t.isVector3?(r[12]=t.x,r[13]=t.y,r[14]=t.z):(r[12]=t,r[13]=e,r[14]=n),this}invert(){const t=this.elements,e=t[0],n=t[1],r=t[2],s=t[3],o=t[4],a=t[5],l=t[6],c=t[7],h=t[8],u=t[9],d=t[10],m=t[11],_=t[12],M=t[13],p=t[14],f=t[15],y=u*p*c-M*d*c+M*l*m-a*p*m-u*l*f+a*d*f,g=_*d*c-h*p*c-_*l*m+o*p*m+h*l*f-o*d*f,E=h*M*c-_*u*c+_*a*m-o*M*m-h*a*f+o*u*f,P=_*u*l-h*M*l-_*a*d+o*M*d+h*a*p-o*u*p,w=e*y+n*g+r*E+s*P;if(w===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);const b=1/w;return t[0]=y*b,t[1]=(M*d*s-u*p*s-M*r*m+n*p*m+u*r*f-n*d*f)*b,t[2]=(a*p*s-M*l*s+M*r*c-n*p*c-a*r*f+n*l*f)*b,t[3]=(u*l*s-a*d*s-u*r*c+n*d*c+a*r*m-n*l*m)*b,t[4]=g*b,t[5]=(h*p*s-_*d*s+_*r*m-e*p*m-h*r*f+e*d*f)*b,t[6]=(_*l*s-o*p*s-_*r*c+e*p*c+o*r*f-e*l*f)*b,t[7]=(o*d*s-h*l*s+h*r*c-e*d*c-o*r*m+e*l*m)*b,t[8]=E*b,t[9]=(_*u*s-h*M*s-_*n*m+e*M*m+h*n*f-e*u*f)*b,t[10]=(o*M*s-_*a*s+_*n*c-e*M*c-o*n*f+e*a*f)*b,t[11]=(h*a*s-o*u*s-h*n*c+e*u*c+o*n*m-e*a*m)*b,t[12]=P*b,t[13]=(h*M*r-_*u*r+_*n*d-e*M*d-h*n*p+e*u*p)*b,t[14]=(_*a*r-o*M*r-_*n*l+e*M*l+o*n*p-e*a*p)*b,t[15]=(o*u*r-h*a*r+h*n*l-e*u*l-o*n*d+e*a*d)*b,this}scale(t){const e=this.elements,n=t.x,r=t.y,s=t.z;return e[0]*=n,e[4]*=r,e[8]*=s,e[1]*=n,e[5]*=r,e[9]*=s,e[2]*=n,e[6]*=r,e[10]*=s,e[3]*=n,e[7]*=r,e[11]*=s,this}getMaxScaleOnAxis(){const t=this.elements,e=t[0]*t[0]+t[1]*t[1]+t[2]*t[2],n=t[4]*t[4]+t[5]*t[5]+t[6]*t[6],r=t[8]*t[8]+t[9]*t[9]+t[10]*t[10];return Math.sqrt(Math.max(e,n,r))}makeTranslation(t,e,n){return t.isVector3?this.set(1,0,0,t.x,0,1,0,t.y,0,0,1,t.z,0,0,0,1):this.set(1,0,0,t,0,1,0,e,0,0,1,n,0,0,0,1),this}makeRotationX(t){const e=Math.cos(t),n=Math.sin(t);return this.set(1,0,0,0,0,e,-n,0,0,n,e,0,0,0,0,1),this}makeRotationY(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,0,n,0,0,1,0,0,-n,0,e,0,0,0,0,1),this}makeRotationZ(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,-n,0,0,n,e,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(t,e){const n=Math.cos(e),r=Math.sin(e),s=1-n,o=t.x,a=t.y,l=t.z,c=s*o,h=s*a;return this.set(c*o+n,c*a-r*l,c*l+r*a,0,c*a+r*l,h*a+n,h*l-r*o,0,c*l-r*a,h*l+r*o,s*l*l+n,0,0,0,0,1),this}makeScale(t,e,n){return this.set(t,0,0,0,0,e,0,0,0,0,n,0,0,0,0,1),this}makeShear(t,e,n,r,s,o){return this.set(1,n,s,0,t,1,o,0,e,r,1,0,0,0,0,1),this}compose(t,e,n){const r=this.elements,s=e._x,o=e._y,a=e._z,l=e._w,c=s+s,h=o+o,u=a+a,d=s*c,m=s*h,_=s*u,M=o*h,p=o*u,f=a*u,y=l*c,g=l*h,E=l*u,P=n.x,w=n.y,b=n.z;return r[0]=(1-(M+f))*P,r[1]=(m+E)*P,r[2]=(_-g)*P,r[3]=0,r[4]=(m-E)*w,r[5]=(1-(d+f))*w,r[6]=(p+y)*w,r[7]=0,r[8]=(_+g)*b,r[9]=(p-y)*b,r[10]=(1-(d+M))*b,r[11]=0,r[12]=t.x,r[13]=t.y,r[14]=t.z,r[15]=1,this}decompose(t,e,n){const r=this.elements;let s=Gn.set(r[0],r[1],r[2]).length();const o=Gn.set(r[4],r[5],r[6]).length(),a=Gn.set(r[8],r[9],r[10]).length();this.determinant()<0&&(s=-s),t.x=r[12],t.y=r[13],t.z=r[14],Ue.copy(this);const c=1/s,h=1/o,u=1/a;return Ue.elements[0]*=c,Ue.elements[1]*=c,Ue.elements[2]*=c,Ue.elements[4]*=h,Ue.elements[5]*=h,Ue.elements[6]*=h,Ue.elements[8]*=u,Ue.elements[9]*=u,Ue.elements[10]*=u,e.setFromRotationMatrix(Ue),n.x=s,n.y=o,n.z=a,this}makePerspective(t,e,n,r,s,o,a=Qe){const l=this.elements,c=2*s/(e-t),h=2*s/(n-r),u=(e+t)/(e-t),d=(n+r)/(n-r);let m,_;if(a===Qe)m=-(o+s)/(o-s),_=-2*o*s/(o-s);else if(a===fr)m=-o/(o-s),_=-o*s/(o-s);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+a);return l[0]=c,l[4]=0,l[8]=u,l[12]=0,l[1]=0,l[5]=h,l[9]=d,l[13]=0,l[2]=0,l[6]=0,l[10]=m,l[14]=_,l[3]=0,l[7]=0,l[11]=-1,l[15]=0,this}makeOrthographic(t,e,n,r,s,o,a=Qe){const l=this.elements,c=1/(e-t),h=1/(n-r),u=1/(o-s),d=(e+t)*c,m=(n+r)*h;let _,M;if(a===Qe)_=(o+s)*u,M=-2*u;else if(a===fr)_=s*u,M=-1*u;else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+a);return l[0]=2*c,l[4]=0,l[8]=0,l[12]=-d,l[1]=0,l[5]=2*h,l[9]=0,l[13]=-m,l[2]=0,l[6]=0,l[10]=M,l[14]=-_,l[3]=0,l[7]=0,l[11]=0,l[15]=1,this}equals(t){const e=this.elements,n=t.elements;for(let r=0;r<16;r++)if(e[r]!==n[r])return!1;return!0}fromArray(t,e=0){for(let n=0;n<16;n++)this.elements[n]=t[n+e];return this}toArray(t=[],e=0){const n=this.elements;return t[e]=n[0],t[e+1]=n[1],t[e+2]=n[2],t[e+3]=n[3],t[e+4]=n[4],t[e+5]=n[5],t[e+6]=n[6],t[e+7]=n[7],t[e+8]=n[8],t[e+9]=n[9],t[e+10]=n[10],t[e+11]=n[11],t[e+12]=n[12],t[e+13]=n[13],t[e+14]=n[14],t[e+15]=n[15],t}}const Gn=new C,Ue=new Jt,Zc=new C(0,0,0),Kc=new C(1,1,1),sn=new C,Gi=new C,Ae=new C,wa=new Jt,Ra=new Pi;class ke{constructor(t=0,e=0,n=0,r=ke.DEFAULT_ORDER){this.isEuler=!0,this._x=t,this._y=e,this._z=n,this._order=r}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get order(){return this._order}set order(t){this._order=t,this._onChangeCallback()}set(t,e,n,r=this._order){return this._x=t,this._y=e,this._z=n,this._order=r,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(t){return this._x=t._x,this._y=t._y,this._z=t._z,this._order=t._order,this._onChangeCallback(),this}setFromRotationMatrix(t,e=this._order,n=!0){const r=t.elements,s=r[0],o=r[4],a=r[8],l=r[1],c=r[5],h=r[9],u=r[2],d=r[6],m=r[10];switch(e){case"XYZ":this._y=Math.asin(ae(a,-1,1)),Math.abs(a)<.9999999?(this._x=Math.atan2(-h,m),this._z=Math.atan2(-o,s)):(this._x=Math.atan2(d,c),this._z=0);break;case"YXZ":this._x=Math.asin(-ae(h,-1,1)),Math.abs(h)<.9999999?(this._y=Math.atan2(a,m),this._z=Math.atan2(l,c)):(this._y=Math.atan2(-u,s),this._z=0);break;case"ZXY":this._x=Math.asin(ae(d,-1,1)),Math.abs(d)<.9999999?(this._y=Math.atan2(-u,m),this._z=Math.atan2(-o,c)):(this._y=0,this._z=Math.atan2(l,s));break;case"ZYX":this._y=Math.asin(-ae(u,-1,1)),Math.abs(u)<.9999999?(this._x=Math.atan2(d,m),this._z=Math.atan2(l,s)):(this._x=0,this._z=Math.atan2(-o,c));break;case"YZX":this._z=Math.asin(ae(l,-1,1)),Math.abs(l)<.9999999?(this._x=Math.atan2(-h,c),this._y=Math.atan2(-u,s)):(this._x=0,this._y=Math.atan2(a,m));break;case"XZY":this._z=Math.asin(-ae(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(d,c),this._y=Math.atan2(a,s)):(this._x=Math.atan2(-h,m),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+e)}return this._order=e,n===!0&&this._onChangeCallback(),this}setFromQuaternion(t,e,n){return wa.makeRotationFromQuaternion(t),this.setFromRotationMatrix(wa,e,n)}setFromVector3(t,e=this._order){return this.set(t.x,t.y,t.z,e)}reorder(t){return Ra.setFromEuler(this),this.setFromQuaternion(Ra,t)}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._order===this._order}fromArray(t){return this._x=t[0],this._y=t[1],this._z=t[2],t[3]!==void 0&&(this._order=t[3]),this._onChangeCallback(),this}toArray(t=[],e=0){return t[e]=this._x,t[e+1]=this._y,t[e+2]=this._z,t[e+3]=this._order,t}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}}ke.DEFAULT_ORDER="XYZ";class Rs{constructor(){this.mask=1}set(t){this.mask=(1<<t|0)>>>0}enable(t){this.mask|=1<<t|0}enableAll(){this.mask=-1}toggle(t){this.mask^=1<<t|0}disable(t){this.mask&=~(1<<t|0)}disableAll(){this.mask=0}test(t){return(this.mask&t.mask)!==0}isEnabled(t){return(this.mask&(1<<t|0))!==0}}let $c=0;const Ca=new C,Hn=new Pi,Je=new Jt,Hi=new C,gi=new C,jc=new C,Qc=new Pi,Pa=new C(1,0,0),La=new C(0,1,0),Da=new C(0,0,1),th={type:"added"},eh={type:"removed"},Vr={type:"childadded",child:null},kr={type:"childremoved",child:null};class ue extends li{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:$c++}),this.uuid=Un(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=ue.DEFAULT_UP.clone();const t=new C,e=new ke,n=new Pi,r=new C(1,1,1);function s(){n.setFromEuler(e,!1)}function o(){e.setFromQuaternion(n,void 0,!1)}e._onChange(s),n._onChange(o),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:t},rotation:{configurable:!0,enumerable:!0,value:e},quaternion:{configurable:!0,enumerable:!0,value:n},scale:{configurable:!0,enumerable:!0,value:r},modelViewMatrix:{value:new Jt},normalMatrix:{value:new Bt}}),this.matrix=new Jt,this.matrixWorld=new Jt,this.matrixAutoUpdate=ue.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=ue.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new Rs,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(t){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(t),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(t){return this.quaternion.premultiply(t),this}setRotationFromAxisAngle(t,e){this.quaternion.setFromAxisAngle(t,e)}setRotationFromEuler(t){this.quaternion.setFromEuler(t,!0)}setRotationFromMatrix(t){this.quaternion.setFromRotationMatrix(t)}setRotationFromQuaternion(t){this.quaternion.copy(t)}rotateOnAxis(t,e){return Hn.setFromAxisAngle(t,e),this.quaternion.multiply(Hn),this}rotateOnWorldAxis(t,e){return Hn.setFromAxisAngle(t,e),this.quaternion.premultiply(Hn),this}rotateX(t){return this.rotateOnAxis(Pa,t)}rotateY(t){return this.rotateOnAxis(La,t)}rotateZ(t){return this.rotateOnAxis(Da,t)}translateOnAxis(t,e){return Ca.copy(t).applyQuaternion(this.quaternion),this.position.add(Ca.multiplyScalar(e)),this}translateX(t){return this.translateOnAxis(Pa,t)}translateY(t){return this.translateOnAxis(La,t)}translateZ(t){return this.translateOnAxis(Da,t)}localToWorld(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(this.matrixWorld)}worldToLocal(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(Je.copy(this.matrixWorld).invert())}lookAt(t,e,n){t.isVector3?Hi.copy(t):Hi.set(t,e,n);const r=this.parent;this.updateWorldMatrix(!0,!1),gi.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?Je.lookAt(gi,Hi,this.up):Je.lookAt(Hi,gi,this.up),this.quaternion.setFromRotationMatrix(Je),r&&(Je.extractRotation(r.matrixWorld),Hn.setFromRotationMatrix(Je),this.quaternion.premultiply(Hn.invert()))}add(t){if(arguments.length>1){for(let e=0;e<arguments.length;e++)this.add(arguments[e]);return this}return t===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",t),this):(t&&t.isObject3D?(t.parent!==null&&t.parent.remove(t),t.parent=this,this.children.push(t),t.dispatchEvent(th),Vr.child=t,this.dispatchEvent(Vr),Vr.child=null):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",t),this)}remove(t){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.remove(arguments[n]);return this}const e=this.children.indexOf(t);return e!==-1&&(t.parent=null,this.children.splice(e,1),t.dispatchEvent(eh),kr.child=t,this.dispatchEvent(kr),kr.child=null),this}removeFromParent(){const t=this.parent;return t!==null&&t.remove(this),this}clear(){return this.remove(...this.children)}attach(t){return this.updateWorldMatrix(!0,!1),Je.copy(this.matrixWorld).invert(),t.parent!==null&&(t.parent.updateWorldMatrix(!0,!1),Je.multiply(t.parent.matrixWorld)),t.applyMatrix4(Je),this.add(t),t.updateWorldMatrix(!1,!0),this}getObjectById(t){return this.getObjectByProperty("id",t)}getObjectByName(t){return this.getObjectByProperty("name",t)}getObjectByProperty(t,e){if(this[t]===e)return this;for(let n=0,r=this.children.length;n<r;n++){const o=this.children[n].getObjectByProperty(t,e);if(o!==void 0)return o}}getObjectsByProperty(t,e,n=[]){this[t]===e&&n.push(this);const r=this.children;for(let s=0,o=r.length;s<o;s++)r[s].getObjectsByProperty(t,e,n);return n}getWorldPosition(t){return this.updateWorldMatrix(!0,!1),t.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(gi,t,jc),t}getWorldScale(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(gi,Qc,t),t}getWorldDirection(t){this.updateWorldMatrix(!0,!1);const e=this.matrixWorld.elements;return t.set(e[8],e[9],e[10]).normalize()}raycast(){}traverse(t){t(this);const e=this.children;for(let n=0,r=e.length;n<r;n++)e[n].traverse(t)}traverseVisible(t){if(this.visible===!1)return;t(this);const e=this.children;for(let n=0,r=e.length;n<r;n++)e[n].traverseVisible(t)}traverseAncestors(t){const e=this.parent;e!==null&&(t(e),e.traverseAncestors(t))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(t){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||t)&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix),this.matrixWorldNeedsUpdate=!1,t=!0);const e=this.children;for(let n=0,r=e.length;n<r;n++){const s=e[n];(s.matrixWorldAutoUpdate===!0||t===!0)&&s.updateMatrixWorld(t)}}updateWorldMatrix(t,e){const n=this.parent;if(t===!0&&n!==null&&n.matrixWorldAutoUpdate===!0&&n.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix),e===!0){const r=this.children;for(let s=0,o=r.length;s<o;s++){const a=r[s];a.matrixWorldAutoUpdate===!0&&a.updateWorldMatrix(!1,!0)}}}toJSON(t){const e=t===void 0||typeof t=="string",n={};e&&(t={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},n.metadata={version:4.6,type:"Object",generator:"Object3D.toJSON"});const r={};r.uuid=this.uuid,r.type=this.type,this.name!==""&&(r.name=this.name),this.castShadow===!0&&(r.castShadow=!0),this.receiveShadow===!0&&(r.receiveShadow=!0),this.visible===!1&&(r.visible=!1),this.frustumCulled===!1&&(r.frustumCulled=!1),this.renderOrder!==0&&(r.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(r.userData=this.userData),r.layers=this.layers.mask,r.matrix=this.matrix.toArray(),r.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(r.matrixAutoUpdate=!1),this.isInstancedMesh&&(r.type="InstancedMesh",r.count=this.count,r.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(r.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(r.type="BatchedMesh",r.perObjectFrustumCulled=this.perObjectFrustumCulled,r.sortObjects=this.sortObjects,r.drawRanges=this._drawRanges,r.reservedRanges=this._reservedRanges,r.visibility=this._visibility,r.active=this._active,r.bounds=this._bounds.map(a=>({boxInitialized:a.boxInitialized,boxMin:a.box.min.toArray(),boxMax:a.box.max.toArray(),sphereInitialized:a.sphereInitialized,sphereRadius:a.sphere.radius,sphereCenter:a.sphere.center.toArray()})),r.maxGeometryCount=this._maxGeometryCount,r.maxVertexCount=this._maxVertexCount,r.maxIndexCount=this._maxIndexCount,r.geometryInitialized=this._geometryInitialized,r.geometryCount=this._geometryCount,r.matricesTexture=this._matricesTexture.toJSON(t),this.boundingSphere!==null&&(r.boundingSphere={center:r.boundingSphere.center.toArray(),radius:r.boundingSphere.radius}),this.boundingBox!==null&&(r.boundingBox={min:r.boundingBox.min.toArray(),max:r.boundingBox.max.toArray()}));function s(a,l){return a[l.uuid]===void 0&&(a[l.uuid]=l.toJSON(t)),l.uuid}if(this.isScene)this.background&&(this.background.isColor?r.background=this.background.toJSON():this.background.isTexture&&(r.background=this.background.toJSON(t).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(r.environment=this.environment.toJSON(t).uuid);else if(this.isMesh||this.isLine||this.isPoints){r.geometry=s(t.geometries,this.geometry);const a=this.geometry.parameters;if(a!==void 0&&a.shapes!==void 0){const l=a.shapes;if(Array.isArray(l))for(let c=0,h=l.length;c<h;c++){const u=l[c];s(t.shapes,u)}else s(t.shapes,l)}}if(this.isSkinnedMesh&&(r.bindMode=this.bindMode,r.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(s(t.skeletons,this.skeleton),r.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){const a=[];for(let l=0,c=this.material.length;l<c;l++)a.push(s(t.materials,this.material[l]));r.material=a}else r.material=s(t.materials,this.material);if(this.children.length>0){r.children=[];for(let a=0;a<this.children.length;a++)r.children.push(this.children[a].toJSON(t).object)}if(this.animations.length>0){r.animations=[];for(let a=0;a<this.animations.length;a++){const l=this.animations[a];r.animations.push(s(t.animations,l))}}if(e){const a=o(t.geometries),l=o(t.materials),c=o(t.textures),h=o(t.images),u=o(t.shapes),d=o(t.skeletons),m=o(t.animations),_=o(t.nodes);a.length>0&&(n.geometries=a),l.length>0&&(n.materials=l),c.length>0&&(n.textures=c),h.length>0&&(n.images=h),u.length>0&&(n.shapes=u),d.length>0&&(n.skeletons=d),m.length>0&&(n.animations=m),_.length>0&&(n.nodes=_)}return n.object=r,n;function o(a){const l=[];for(const c in a){const h=a[c];delete h.metadata,l.push(h)}return l}}clone(t){return new this.constructor().copy(this,t)}copy(t,e=!0){if(this.name=t.name,this.up.copy(t.up),this.position.copy(t.position),this.rotation.order=t.rotation.order,this.quaternion.copy(t.quaternion),this.scale.copy(t.scale),this.matrix.copy(t.matrix),this.matrixWorld.copy(t.matrixWorld),this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrixWorldAutoUpdate=t.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=t.matrixWorldNeedsUpdate,this.layers.mask=t.layers.mask,this.visible=t.visible,this.castShadow=t.castShadow,this.receiveShadow=t.receiveShadow,this.frustumCulled=t.frustumCulled,this.renderOrder=t.renderOrder,this.animations=t.animations.slice(),this.userData=JSON.parse(JSON.stringify(t.userData)),e===!0)for(let n=0;n<t.children.length;n++){const r=t.children[n];this.add(r.clone())}return this}}ue.DEFAULT_UP=new C(0,1,0);ue.DEFAULT_MATRIX_AUTO_UPDATE=!0;ue.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;const Ie=new C,Ze=new C,Wr=new C,Ke=new C,Vn=new C,kn=new C,Ua=new C,Xr=new C,qr=new C,Yr=new C;class Ve{constructor(t=new C,e=new C,n=new C){this.a=t,this.b=e,this.c=n}static getNormal(t,e,n,r){r.subVectors(n,e),Ie.subVectors(t,e),r.cross(Ie);const s=r.lengthSq();return s>0?r.multiplyScalar(1/Math.sqrt(s)):r.set(0,0,0)}static getBarycoord(t,e,n,r,s){Ie.subVectors(r,e),Ze.subVectors(n,e),Wr.subVectors(t,e);const o=Ie.dot(Ie),a=Ie.dot(Ze),l=Ie.dot(Wr),c=Ze.dot(Ze),h=Ze.dot(Wr),u=o*c-a*a;if(u===0)return s.set(0,0,0),null;const d=1/u,m=(c*l-a*h)*d,_=(o*h-a*l)*d;return s.set(1-m-_,_,m)}static containsPoint(t,e,n,r){return this.getBarycoord(t,e,n,r,Ke)===null?!1:Ke.x>=0&&Ke.y>=0&&Ke.x+Ke.y<=1}static getInterpolation(t,e,n,r,s,o,a,l){return this.getBarycoord(t,e,n,r,Ke)===null?(l.x=0,l.y=0,"z"in l&&(l.z=0),"w"in l&&(l.w=0),null):(l.setScalar(0),l.addScaledVector(s,Ke.x),l.addScaledVector(o,Ke.y),l.addScaledVector(a,Ke.z),l)}static isFrontFacing(t,e,n,r){return Ie.subVectors(n,e),Ze.subVectors(t,e),Ie.cross(Ze).dot(r)<0}set(t,e,n){return this.a.copy(t),this.b.copy(e),this.c.copy(n),this}setFromPointsAndIndices(t,e,n,r){return this.a.copy(t[e]),this.b.copy(t[n]),this.c.copy(t[r]),this}setFromAttributeAndIndices(t,e,n,r){return this.a.fromBufferAttribute(t,e),this.b.fromBufferAttribute(t,n),this.c.fromBufferAttribute(t,r),this}clone(){return new this.constructor().copy(this)}copy(t){return this.a.copy(t.a),this.b.copy(t.b),this.c.copy(t.c),this}getArea(){return Ie.subVectors(this.c,this.b),Ze.subVectors(this.a,this.b),Ie.cross(Ze).length()*.5}getMidpoint(t){return t.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(t){return Ve.getNormal(this.a,this.b,this.c,t)}getPlane(t){return t.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(t,e){return Ve.getBarycoord(t,this.a,this.b,this.c,e)}getInterpolation(t,e,n,r,s){return Ve.getInterpolation(t,this.a,this.b,this.c,e,n,r,s)}containsPoint(t){return Ve.containsPoint(t,this.a,this.b,this.c)}isFrontFacing(t){return Ve.isFrontFacing(this.a,this.b,this.c,t)}intersectsBox(t){return t.intersectsTriangle(this)}closestPointToPoint(t,e){const n=this.a,r=this.b,s=this.c;let o,a;Vn.subVectors(r,n),kn.subVectors(s,n),Xr.subVectors(t,n);const l=Vn.dot(Xr),c=kn.dot(Xr);if(l<=0&&c<=0)return e.copy(n);qr.subVectors(t,r);const h=Vn.dot(qr),u=kn.dot(qr);if(h>=0&&u<=h)return e.copy(r);const d=l*u-h*c;if(d<=0&&l>=0&&h<=0)return o=l/(l-h),e.copy(n).addScaledVector(Vn,o);Yr.subVectors(t,s);const m=Vn.dot(Yr),_=kn.dot(Yr);if(_>=0&&m<=_)return e.copy(s);const M=m*c-l*_;if(M<=0&&c>=0&&_<=0)return a=c/(c-_),e.copy(n).addScaledVector(kn,a);const p=h*_-m*u;if(p<=0&&u-h>=0&&m-_>=0)return Ua.subVectors(s,r),a=(u-h)/(u-h+(m-_)),e.copy(r).addScaledVector(Ua,a);const f=1/(p+M+d);return o=M*f,a=d*f,e.copy(n).addScaledVector(Vn,o).addScaledVector(kn,a)}equals(t){return t.a.equals(this.a)&&t.b.equals(this.b)&&t.c.equals(this.c)}}const qo={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},an={h:0,s:0,l:0},Vi={h:0,s:0,l:0};function Jr(i,t,e){return e<0&&(e+=1),e>1&&(e-=1),e<1/6?i+(t-i)*6*e:e<1/2?t:e<2/3?i+(t-i)*6*(2/3-e):i}class zt{constructor(t,e,n){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(t,e,n)}set(t,e,n){if(e===void 0&&n===void 0){const r=t;r&&r.isColor?this.copy(r):typeof r=="number"?this.setHex(r):typeof r=="string"&&this.setStyle(r)}else this.setRGB(t,e,n);return this}setScalar(t){return this.r=t,this.g=t,this.b=t,this}setHex(t,e=ze){return t=Math.floor(t),this.r=(t>>16&255)/255,this.g=(t>>8&255)/255,this.b=(t&255)/255,Yt.toWorkingColorSpace(this,e),this}setRGB(t,e,n,r=Yt.workingColorSpace){return this.r=t,this.g=e,this.b=n,Yt.toWorkingColorSpace(this,r),this}setHSL(t,e,n,r=Yt.workingColorSpace){if(t=bs(t,1),e=ae(e,0,1),n=ae(n,0,1),e===0)this.r=this.g=this.b=n;else{const s=n<=.5?n*(1+e):n+e-n*e,o=2*n-s;this.r=Jr(o,s,t+1/3),this.g=Jr(o,s,t),this.b=Jr(o,s,t-1/3)}return Yt.toWorkingColorSpace(this,r),this}setStyle(t,e=ze){function n(s){s!==void 0&&parseFloat(s)<1&&console.warn("THREE.Color: Alpha component of "+t+" will be ignored.")}let r;if(r=/^(\w+)\(([^\)]*)\)/.exec(t)){let s;const o=r[1],a=r[2];switch(o){case"rgb":case"rgba":if(s=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(s[4]),this.setRGB(Math.min(255,parseInt(s[1],10))/255,Math.min(255,parseInt(s[2],10))/255,Math.min(255,parseInt(s[3],10))/255,e);if(s=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(s[4]),this.setRGB(Math.min(100,parseInt(s[1],10))/100,Math.min(100,parseInt(s[2],10))/100,Math.min(100,parseInt(s[3],10))/100,e);break;case"hsl":case"hsla":if(s=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(s[4]),this.setHSL(parseFloat(s[1])/360,parseFloat(s[2])/100,parseFloat(s[3])/100,e);break;default:console.warn("THREE.Color: Unknown color model "+t)}}else if(r=/^\#([A-Fa-f\d]+)$/.exec(t)){const s=r[1],o=s.length;if(o===3)return this.setRGB(parseInt(s.charAt(0),16)/15,parseInt(s.charAt(1),16)/15,parseInt(s.charAt(2),16)/15,e);if(o===6)return this.setHex(parseInt(s,16),e);console.warn("THREE.Color: Invalid hex color "+t)}else if(t&&t.length>0)return this.setColorName(t,e);return this}setColorName(t,e=ze){const n=qo[t.toLowerCase()];return n!==void 0?this.setHex(n,e):console.warn("THREE.Color: Unknown color "+t),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(t){return this.r=t.r,this.g=t.g,this.b=t.b,this}copySRGBToLinear(t){return this.r=ii(t.r),this.g=ii(t.g),this.b=ii(t.b),this}copyLinearToSRGB(t){return this.r=Ir(t.r),this.g=Ir(t.g),this.b=Ir(t.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(t=ze){return Yt.fromWorkingColorSpace(_e.copy(this),t),Math.round(ae(_e.r*255,0,255))*65536+Math.round(ae(_e.g*255,0,255))*256+Math.round(ae(_e.b*255,0,255))}getHexString(t=ze){return("000000"+this.getHex(t).toString(16)).slice(-6)}getHSL(t,e=Yt.workingColorSpace){Yt.fromWorkingColorSpace(_e.copy(this),e);const n=_e.r,r=_e.g,s=_e.b,o=Math.max(n,r,s),a=Math.min(n,r,s);let l,c;const h=(a+o)/2;if(a===o)l=0,c=0;else{const u=o-a;switch(c=h<=.5?u/(o+a):u/(2-o-a),o){case n:l=(r-s)/u+(r<s?6:0);break;case r:l=(s-n)/u+2;break;case s:l=(n-r)/u+4;break}l/=6}return t.h=l,t.s=c,t.l=h,t}getRGB(t,e=Yt.workingColorSpace){return Yt.fromWorkingColorSpace(_e.copy(this),e),t.r=_e.r,t.g=_e.g,t.b=_e.b,t}getStyle(t=ze){Yt.fromWorkingColorSpace(_e.copy(this),t);const e=_e.r,n=_e.g,r=_e.b;return t!==ze?`color(${t} ${e.toFixed(3)} ${n.toFixed(3)} ${r.toFixed(3)})`:`rgb(${Math.round(e*255)},${Math.round(n*255)},${Math.round(r*255)})`}offsetHSL(t,e,n){return this.getHSL(an),this.setHSL(an.h+t,an.s+e,an.l+n)}add(t){return this.r+=t.r,this.g+=t.g,this.b+=t.b,this}addColors(t,e){return this.r=t.r+e.r,this.g=t.g+e.g,this.b=t.b+e.b,this}addScalar(t){return this.r+=t,this.g+=t,this.b+=t,this}sub(t){return this.r=Math.max(0,this.r-t.r),this.g=Math.max(0,this.g-t.g),this.b=Math.max(0,this.b-t.b),this}multiply(t){return this.r*=t.r,this.g*=t.g,this.b*=t.b,this}multiplyScalar(t){return this.r*=t,this.g*=t,this.b*=t,this}lerp(t,e){return this.r+=(t.r-this.r)*e,this.g+=(t.g-this.g)*e,this.b+=(t.b-this.b)*e,this}lerpColors(t,e,n){return this.r=t.r+(e.r-t.r)*n,this.g=t.g+(e.g-t.g)*n,this.b=t.b+(e.b-t.b)*n,this}lerpHSL(t,e){this.getHSL(an),t.getHSL(Vi);const n=yi(an.h,Vi.h,e),r=yi(an.s,Vi.s,e),s=yi(an.l,Vi.l,e);return this.setHSL(n,r,s),this}setFromVector3(t){return this.r=t.x,this.g=t.y,this.b=t.z,this}applyMatrix3(t){const e=this.r,n=this.g,r=this.b,s=t.elements;return this.r=s[0]*e+s[3]*n+s[6]*r,this.g=s[1]*e+s[4]*n+s[7]*r,this.b=s[2]*e+s[5]*n+s[8]*r,this}equals(t){return t.r===this.r&&t.g===this.g&&t.b===this.b}fromArray(t,e=0){return this.r=t[e],this.g=t[e+1],this.b=t[e+2],this}toArray(t=[],e=0){return t[e]=this.r,t[e+1]=this.g,t[e+2]=this.b,t}fromBufferAttribute(t,e){return this.r=t.getX(e),this.g=t.getY(e),this.b=t.getZ(e),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}}const _e=new zt;zt.NAMES=qo;let nh=0;class hi extends li{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:nh++}),this.uuid=Un(),this.name="",this.type="Material",this.blending=ni,this.side=pn,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=hs,this.blendDst=us,this.blendEquation=bn,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new zt(0,0,0),this.blendAlpha=0,this.depthFunc=lr,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=xa,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=Nn,this.stencilZFail=Nn,this.stencilZPass=Nn,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(t){this._alphaTest>0!=t>0&&this.version++,this._alphaTest=t}onBuild(){}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(t){if(t!==void 0)for(const e in t){const n=t[e];if(n===void 0){console.warn(`THREE.Material: parameter '${e}' has value of undefined.`);continue}const r=this[e];if(r===void 0){console.warn(`THREE.Material: '${e}' is not a property of THREE.${this.type}.`);continue}r&&r.isColor?r.set(n):r&&r.isVector3&&n&&n.isVector3?r.copy(n):this[e]=n}}toJSON(t){const e=t===void 0||typeof t=="string";e&&(t={textures:{},images:{}});const n={metadata:{version:4.6,type:"Material",generator:"Material.toJSON"}};n.uuid=this.uuid,n.type=this.type,this.name!==""&&(n.name=this.name),this.color&&this.color.isColor&&(n.color=this.color.getHex()),this.roughness!==void 0&&(n.roughness=this.roughness),this.metalness!==void 0&&(n.metalness=this.metalness),this.sheen!==void 0&&(n.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(n.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(n.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(n.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(n.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(n.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(n.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(n.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(n.shininess=this.shininess),this.clearcoat!==void 0&&(n.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(n.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(n.clearcoatMap=this.clearcoatMap.toJSON(t).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(n.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(t).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(n.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(t).uuid,n.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.iridescence!==void 0&&(n.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(n.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(n.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(n.iridescenceMap=this.iridescenceMap.toJSON(t).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(n.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(t).uuid),this.anisotropy!==void 0&&(n.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(n.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(n.anisotropyMap=this.anisotropyMap.toJSON(t).uuid),this.map&&this.map.isTexture&&(n.map=this.map.toJSON(t).uuid),this.matcap&&this.matcap.isTexture&&(n.matcap=this.matcap.toJSON(t).uuid),this.alphaMap&&this.alphaMap.isTexture&&(n.alphaMap=this.alphaMap.toJSON(t).uuid),this.lightMap&&this.lightMap.isTexture&&(n.lightMap=this.lightMap.toJSON(t).uuid,n.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(n.aoMap=this.aoMap.toJSON(t).uuid,n.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(n.bumpMap=this.bumpMap.toJSON(t).uuid,n.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(n.normalMap=this.normalMap.toJSON(t).uuid,n.normalMapType=this.normalMapType,n.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(n.displacementMap=this.displacementMap.toJSON(t).uuid,n.displacementScale=this.displacementScale,n.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(n.roughnessMap=this.roughnessMap.toJSON(t).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(n.metalnessMap=this.metalnessMap.toJSON(t).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(n.emissiveMap=this.emissiveMap.toJSON(t).uuid),this.specularMap&&this.specularMap.isTexture&&(n.specularMap=this.specularMap.toJSON(t).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(n.specularIntensityMap=this.specularIntensityMap.toJSON(t).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(n.specularColorMap=this.specularColorMap.toJSON(t).uuid),this.envMap&&this.envMap.isTexture&&(n.envMap=this.envMap.toJSON(t).uuid,this.combine!==void 0&&(n.combine=this.combine)),this.envMapRotation!==void 0&&(n.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(n.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(n.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(n.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(n.gradientMap=this.gradientMap.toJSON(t).uuid),this.transmission!==void 0&&(n.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(n.transmissionMap=this.transmissionMap.toJSON(t).uuid),this.thickness!==void 0&&(n.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(n.thicknessMap=this.thicknessMap.toJSON(t).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(n.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(n.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(n.size=this.size),this.shadowSide!==null&&(n.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(n.sizeAttenuation=this.sizeAttenuation),this.blending!==ni&&(n.blending=this.blending),this.side!==pn&&(n.side=this.side),this.vertexColors===!0&&(n.vertexColors=!0),this.opacity<1&&(n.opacity=this.opacity),this.transparent===!0&&(n.transparent=!0),this.blendSrc!==hs&&(n.blendSrc=this.blendSrc),this.blendDst!==us&&(n.blendDst=this.blendDst),this.blendEquation!==bn&&(n.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(n.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(n.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(n.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(n.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(n.blendAlpha=this.blendAlpha),this.depthFunc!==lr&&(n.depthFunc=this.depthFunc),this.depthTest===!1&&(n.depthTest=this.depthTest),this.depthWrite===!1&&(n.depthWrite=this.depthWrite),this.colorWrite===!1&&(n.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(n.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==xa&&(n.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(n.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(n.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==Nn&&(n.stencilFail=this.stencilFail),this.stencilZFail!==Nn&&(n.stencilZFail=this.stencilZFail),this.stencilZPass!==Nn&&(n.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(n.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(n.rotation=this.rotation),this.polygonOffset===!0&&(n.polygonOffset=!0),this.polygonOffsetFactor!==0&&(n.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(n.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(n.linewidth=this.linewidth),this.dashSize!==void 0&&(n.dashSize=this.dashSize),this.gapSize!==void 0&&(n.gapSize=this.gapSize),this.scale!==void 0&&(n.scale=this.scale),this.dithering===!0&&(n.dithering=!0),this.alphaTest>0&&(n.alphaTest=this.alphaTest),this.alphaHash===!0&&(n.alphaHash=!0),this.alphaToCoverage===!0&&(n.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(n.premultipliedAlpha=!0),this.forceSinglePass===!0&&(n.forceSinglePass=!0),this.wireframe===!0&&(n.wireframe=!0),this.wireframeLinewidth>1&&(n.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(n.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(n.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(n.flatShading=!0),this.visible===!1&&(n.visible=!1),this.toneMapped===!1&&(n.toneMapped=!1),this.fog===!1&&(n.fog=!1),Object.keys(this.userData).length>0&&(n.userData=this.userData);function r(s){const o=[];for(const a in s){const l=s[a];delete l.metadata,o.push(l)}return o}if(e){const s=r(t.textures),o=r(t.images);s.length>0&&(n.textures=s),o.length>0&&(n.images=o)}return n}clone(){return new this.constructor().copy(this)}copy(t){this.name=t.name,this.blending=t.blending,this.side=t.side,this.vertexColors=t.vertexColors,this.opacity=t.opacity,this.transparent=t.transparent,this.blendSrc=t.blendSrc,this.blendDst=t.blendDst,this.blendEquation=t.blendEquation,this.blendSrcAlpha=t.blendSrcAlpha,this.blendDstAlpha=t.blendDstAlpha,this.blendEquationAlpha=t.blendEquationAlpha,this.blendColor.copy(t.blendColor),this.blendAlpha=t.blendAlpha,this.depthFunc=t.depthFunc,this.depthTest=t.depthTest,this.depthWrite=t.depthWrite,this.stencilWriteMask=t.stencilWriteMask,this.stencilFunc=t.stencilFunc,this.stencilRef=t.stencilRef,this.stencilFuncMask=t.stencilFuncMask,this.stencilFail=t.stencilFail,this.stencilZFail=t.stencilZFail,this.stencilZPass=t.stencilZPass,this.stencilWrite=t.stencilWrite;const e=t.clippingPlanes;let n=null;if(e!==null){const r=e.length;n=new Array(r);for(let s=0;s!==r;++s)n[s]=e[s].clone()}return this.clippingPlanes=n,this.clipIntersection=t.clipIntersection,this.clipShadows=t.clipShadows,this.shadowSide=t.shadowSide,this.colorWrite=t.colorWrite,this.precision=t.precision,this.polygonOffset=t.polygonOffset,this.polygonOffsetFactor=t.polygonOffsetFactor,this.polygonOffsetUnits=t.polygonOffsetUnits,this.dithering=t.dithering,this.alphaTest=t.alphaTest,this.alphaHash=t.alphaHash,this.alphaToCoverage=t.alphaToCoverage,this.premultipliedAlpha=t.premultipliedAlpha,this.forceSinglePass=t.forceSinglePass,this.visible=t.visible,this.toneMapped=t.toneMapped,this.userData=JSON.parse(JSON.stringify(t.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(t){t===!0&&this.version++}}class Yo extends hi{constructor(t){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new zt(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new ke,this.combine=Po,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.specularMap=t.specularMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.combine=t.combine,this.reflectivity=t.reflectivity,this.refractionRatio=t.refractionRatio,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.fog=t.fog,this}}const se=new C,ki=new it;class Le{constructor(t,e,n=!1){if(Array.isArray(t))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,this.name="",this.array=t,this.itemSize=e,this.count=t!==void 0?t.length/e:0,this.normalized=n,this.usage=Ma,this._updateRange={offset:0,count:-1},this.updateRanges=[],this.gpuType=He,this.version=0}onUploadCallback(){}set needsUpdate(t){t===!0&&this.version++}get updateRange(){return Vc("THREE.BufferAttribute: updateRange() is deprecated and will be removed in r169. Use addUpdateRange() instead."),this._updateRange}setUsage(t){return this.usage=t,this}addUpdateRange(t,e){this.updateRanges.push({start:t,count:e})}clearUpdateRanges(){this.updateRanges.length=0}copy(t){return this.name=t.name,this.array=new t.array.constructor(t.array),this.itemSize=t.itemSize,this.count=t.count,this.normalized=t.normalized,this.usage=t.usage,this.gpuType=t.gpuType,this}copyAt(t,e,n){t*=this.itemSize,n*=e.itemSize;for(let r=0,s=this.itemSize;r<s;r++)this.array[t+r]=e.array[n+r];return this}copyArray(t){return this.array.set(t),this}applyMatrix3(t){if(this.itemSize===2)for(let e=0,n=this.count;e<n;e++)ki.fromBufferAttribute(this,e),ki.applyMatrix3(t),this.setXY(e,ki.x,ki.y);else if(this.itemSize===3)for(let e=0,n=this.count;e<n;e++)se.fromBufferAttribute(this,e),se.applyMatrix3(t),this.setXYZ(e,se.x,se.y,se.z);return this}applyMatrix4(t){for(let e=0,n=this.count;e<n;e++)se.fromBufferAttribute(this,e),se.applyMatrix4(t),this.setXYZ(e,se.x,se.y,se.z);return this}applyNormalMatrix(t){for(let e=0,n=this.count;e<n;e++)se.fromBufferAttribute(this,e),se.applyNormalMatrix(t),this.setXYZ(e,se.x,se.y,se.z);return this}transformDirection(t){for(let e=0,n=this.count;e<n;e++)se.fromBufferAttribute(this,e),se.transformDirection(t),this.setXYZ(e,se.x,se.y,se.z);return this}set(t,e=0){return this.array.set(t,e),this}getComponent(t,e){let n=this.array[t*this.itemSize+e];return this.normalized&&(n=jn(n,this.array)),n}setComponent(t,e,n){return this.normalized&&(n=Me(n,this.array)),this.array[t*this.itemSize+e]=n,this}getX(t){let e=this.array[t*this.itemSize];return this.normalized&&(e=jn(e,this.array)),e}setX(t,e){return this.normalized&&(e=Me(e,this.array)),this.array[t*this.itemSize]=e,this}getY(t){let e=this.array[t*this.itemSize+1];return this.normalized&&(e=jn(e,this.array)),e}setY(t,e){return this.normalized&&(e=Me(e,this.array)),this.array[t*this.itemSize+1]=e,this}getZ(t){let e=this.array[t*this.itemSize+2];return this.normalized&&(e=jn(e,this.array)),e}setZ(t,e){return this.normalized&&(e=Me(e,this.array)),this.array[t*this.itemSize+2]=e,this}getW(t){let e=this.array[t*this.itemSize+3];return this.normalized&&(e=jn(e,this.array)),e}setW(t,e){return this.normalized&&(e=Me(e,this.array)),this.array[t*this.itemSize+3]=e,this}setXY(t,e,n){return t*=this.itemSize,this.normalized&&(e=Me(e,this.array),n=Me(n,this.array)),this.array[t+0]=e,this.array[t+1]=n,this}setXYZ(t,e,n,r){return t*=this.itemSize,this.normalized&&(e=Me(e,this.array),n=Me(n,this.array),r=Me(r,this.array)),this.array[t+0]=e,this.array[t+1]=n,this.array[t+2]=r,this}setXYZW(t,e,n,r,s){return t*=this.itemSize,this.normalized&&(e=Me(e,this.array),n=Me(n,this.array),r=Me(r,this.array),s=Me(s,this.array)),this.array[t+0]=e,this.array[t+1]=n,this.array[t+2]=r,this.array[t+3]=s,this}onUpload(t){return this.onUploadCallback=t,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){const t={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(t.name=this.name),this.usage!==Ma&&(t.usage=this.usage),t}}class Jo extends Le{constructor(t,e,n){super(new Uint16Array(t),e,n)}}class Zo extends Le{constructor(t,e,n){super(new Uint32Array(t),e,n)}}class qt extends Le{constructor(t,e,n){super(new Float32Array(t),e,n)}}let ih=0;const Ce=new Jt,Zr=new ue,Wn=new C,be=new In,_i=new In,he=new C;class pe extends li{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:ih++}),this.uuid=Un(),this.name="",this.type="BufferGeometry",this.index=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(t){return Array.isArray(t)?this.index=new(Vo(t)?Zo:Jo)(t,1):this.index=t,this}getAttribute(t){return this.attributes[t]}setAttribute(t,e){return this.attributes[t]=e,this}deleteAttribute(t){return delete this.attributes[t],this}hasAttribute(t){return this.attributes[t]!==void 0}addGroup(t,e,n=0){this.groups.push({start:t,count:e,materialIndex:n})}clearGroups(){this.groups=[]}setDrawRange(t,e){this.drawRange.start=t,this.drawRange.count=e}applyMatrix4(t){const e=this.attributes.position;e!==void 0&&(e.applyMatrix4(t),e.needsUpdate=!0);const n=this.attributes.normal;if(n!==void 0){const s=new Bt().getNormalMatrix(t);n.applyNormalMatrix(s),n.needsUpdate=!0}const r=this.attributes.tangent;return r!==void 0&&(r.transformDirection(t),r.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(t){return Ce.makeRotationFromQuaternion(t),this.applyMatrix4(Ce),this}rotateX(t){return Ce.makeRotationX(t),this.applyMatrix4(Ce),this}rotateY(t){return Ce.makeRotationY(t),this.applyMatrix4(Ce),this}rotateZ(t){return Ce.makeRotationZ(t),this.applyMatrix4(Ce),this}translate(t,e,n){return Ce.makeTranslation(t,e,n),this.applyMatrix4(Ce),this}scale(t,e,n){return Ce.makeScale(t,e,n),this.applyMatrix4(Ce),this}lookAt(t){return Zr.lookAt(t),Zr.updateMatrix(),this.applyMatrix4(Zr.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(Wn).negate(),this.translate(Wn.x,Wn.y,Wn.z),this}setFromPoints(t){const e=[];for(let n=0,r=t.length;n<r;n++){const s=t[n];e.push(s.x,s.y,s.z||0)}return this.setAttribute("position",new qt(e,3)),this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new In);const t=this.attributes.position,e=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new C(-1/0,-1/0,-1/0),new C(1/0,1/0,1/0));return}if(t!==void 0){if(this.boundingBox.setFromBufferAttribute(t),e)for(let n=0,r=e.length;n<r;n++){const s=e[n];be.setFromBufferAttribute(s),this.morphTargetsRelative?(he.addVectors(this.boundingBox.min,be.min),this.boundingBox.expandByPoint(he),he.addVectors(this.boundingBox.max,be.max),this.boundingBox.expandByPoint(he)):(this.boundingBox.expandByPoint(be.min),this.boundingBox.expandByPoint(be.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new ci);const t=this.attributes.position,e=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new C,1/0);return}if(t){const n=this.boundingSphere.center;if(be.setFromBufferAttribute(t),e)for(let s=0,o=e.length;s<o;s++){const a=e[s];_i.setFromBufferAttribute(a),this.morphTargetsRelative?(he.addVectors(be.min,_i.min),be.expandByPoint(he),he.addVectors(be.max,_i.max),be.expandByPoint(he)):(be.expandByPoint(_i.min),be.expandByPoint(_i.max))}be.getCenter(n);let r=0;for(let s=0,o=t.count;s<o;s++)he.fromBufferAttribute(t,s),r=Math.max(r,n.distanceToSquared(he));if(e)for(let s=0,o=e.length;s<o;s++){const a=e[s],l=this.morphTargetsRelative;for(let c=0,h=a.count;c<h;c++)he.fromBufferAttribute(a,c),l&&(Wn.fromBufferAttribute(t,c),he.add(Wn)),r=Math.max(r,n.distanceToSquared(he))}this.boundingSphere.radius=Math.sqrt(r),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){const t=this.index,e=this.attributes;if(t===null||e.position===void 0||e.normal===void 0||e.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}const n=e.position,r=e.normal,s=e.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new Le(new Float32Array(4*n.count),4));const o=this.getAttribute("tangent"),a=[],l=[];for(let U=0;U<n.count;U++)a[U]=new C,l[U]=new C;const c=new C,h=new C,u=new C,d=new it,m=new it,_=new it,M=new C,p=new C;function f(U,V,v){c.fromBufferAttribute(n,U),h.fromBufferAttribute(n,V),u.fromBufferAttribute(n,v),d.fromBufferAttribute(s,U),m.fromBufferAttribute(s,V),_.fromBufferAttribute(s,v),h.sub(c),u.sub(c),m.sub(d),_.sub(d);const A=1/(m.x*_.y-_.x*m.y);isFinite(A)&&(M.copy(h).multiplyScalar(_.y).addScaledVector(u,-m.y).multiplyScalar(A),p.copy(u).multiplyScalar(m.x).addScaledVector(h,-_.x).multiplyScalar(A),a[U].add(M),a[V].add(M),a[v].add(M),l[U].add(p),l[V].add(p),l[v].add(p))}let y=this.groups;y.length===0&&(y=[{start:0,count:t.count}]);for(let U=0,V=y.length;U<V;++U){const v=y[U],A=v.start,Z=v.count;for(let K=A,L=A+Z;K<L;K+=3)f(t.getX(K+0),t.getX(K+1),t.getX(K+2))}const g=new C,E=new C,P=new C,w=new C;function b(U){P.fromBufferAttribute(r,U),w.copy(P);const V=a[U];g.copy(V),g.sub(P.multiplyScalar(P.dot(V))).normalize(),E.crossVectors(w,V);const A=E.dot(l[U])<0?-1:1;o.setXYZW(U,g.x,g.y,g.z,A)}for(let U=0,V=y.length;U<V;++U){const v=y[U],A=v.start,Z=v.count;for(let K=A,L=A+Z;K<L;K+=3)b(t.getX(K+0)),b(t.getX(K+1)),b(t.getX(K+2))}}computeVertexNormals(){const t=this.index,e=this.getAttribute("position");if(e!==void 0){let n=this.getAttribute("normal");if(n===void 0)n=new Le(new Float32Array(e.count*3),3),this.setAttribute("normal",n);else for(let d=0,m=n.count;d<m;d++)n.setXYZ(d,0,0,0);const r=new C,s=new C,o=new C,a=new C,l=new C,c=new C,h=new C,u=new C;if(t)for(let d=0,m=t.count;d<m;d+=3){const _=t.getX(d+0),M=t.getX(d+1),p=t.getX(d+2);r.fromBufferAttribute(e,_),s.fromBufferAttribute(e,M),o.fromBufferAttribute(e,p),h.subVectors(o,s),u.subVectors(r,s),h.cross(u),a.fromBufferAttribute(n,_),l.fromBufferAttribute(n,M),c.fromBufferAttribute(n,p),a.add(h),l.add(h),c.add(h),n.setXYZ(_,a.x,a.y,a.z),n.setXYZ(M,l.x,l.y,l.z),n.setXYZ(p,c.x,c.y,c.z)}else for(let d=0,m=e.count;d<m;d+=3)r.fromBufferAttribute(e,d+0),s.fromBufferAttribute(e,d+1),o.fromBufferAttribute(e,d+2),h.subVectors(o,s),u.subVectors(r,s),h.cross(u),n.setXYZ(d+0,h.x,h.y,h.z),n.setXYZ(d+1,h.x,h.y,h.z),n.setXYZ(d+2,h.x,h.y,h.z);this.normalizeNormals(),n.needsUpdate=!0}}normalizeNormals(){const t=this.attributes.normal;for(let e=0,n=t.count;e<n;e++)he.fromBufferAttribute(t,e),he.normalize(),t.setXYZ(e,he.x,he.y,he.z)}toNonIndexed(){function t(a,l){const c=a.array,h=a.itemSize,u=a.normalized,d=new c.constructor(l.length*h);let m=0,_=0;for(let M=0,p=l.length;M<p;M++){a.isInterleavedBufferAttribute?m=l[M]*a.data.stride+a.offset:m=l[M]*h;for(let f=0;f<h;f++)d[_++]=c[m++]}return new Le(d,h,u)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;const e=new pe,n=this.index.array,r=this.attributes;for(const a in r){const l=r[a],c=t(l,n);e.setAttribute(a,c)}const s=this.morphAttributes;for(const a in s){const l=[],c=s[a];for(let h=0,u=c.length;h<u;h++){const d=c[h],m=t(d,n);l.push(m)}e.morphAttributes[a]=l}e.morphTargetsRelative=this.morphTargetsRelative;const o=this.groups;for(let a=0,l=o.length;a<l;a++){const c=o[a];e.addGroup(c.start,c.count,c.materialIndex)}return e}toJSON(){const t={metadata:{version:4.6,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(t.uuid=this.uuid,t.type=this.type,this.name!==""&&(t.name=this.name),Object.keys(this.userData).length>0&&(t.userData=this.userData),this.parameters!==void 0){const l=this.parameters;for(const c in l)l[c]!==void 0&&(t[c]=l[c]);return t}t.data={attributes:{}};const e=this.index;e!==null&&(t.data.index={type:e.array.constructor.name,array:Array.prototype.slice.call(e.array)});const n=this.attributes;for(const l in n){const c=n[l];t.data.attributes[l]=c.toJSON(t.data)}const r={};let s=!1;for(const l in this.morphAttributes){const c=this.morphAttributes[l],h=[];for(let u=0,d=c.length;u<d;u++){const m=c[u];h.push(m.toJSON(t.data))}h.length>0&&(r[l]=h,s=!0)}s&&(t.data.morphAttributes=r,t.data.morphTargetsRelative=this.morphTargetsRelative);const o=this.groups;o.length>0&&(t.data.groups=JSON.parse(JSON.stringify(o)));const a=this.boundingSphere;return a!==null&&(t.data.boundingSphere={center:a.center.toArray(),radius:a.radius}),t}clone(){return new this.constructor().copy(this)}copy(t){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;const e={};this.name=t.name;const n=t.index;n!==null&&this.setIndex(n.clone(e));const r=t.attributes;for(const c in r){const h=r[c];this.setAttribute(c,h.clone(e))}const s=t.morphAttributes;for(const c in s){const h=[],u=s[c];for(let d=0,m=u.length;d<m;d++)h.push(u[d].clone(e));this.morphAttributes[c]=h}this.morphTargetsRelative=t.morphTargetsRelative;const o=t.groups;for(let c=0,h=o.length;c<h;c++){const u=o[c];this.addGroup(u.start,u.count,u.materialIndex)}const a=t.boundingBox;a!==null&&(this.boundingBox=a.clone());const l=t.boundingSphere;return l!==null&&(this.boundingSphere=l.clone()),this.drawRange.start=t.drawRange.start,this.drawRange.count=t.drawRange.count,this.userData=t.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}}const Ia=new Jt,Mn=new ws,Wi=new ci,Na=new C,Xn=new C,qn=new C,Yn=new C,Kr=new C,Xi=new C,qi=new it,Yi=new it,Ji=new it,Fa=new C,Oa=new C,Ba=new C,Zi=new C,Ki=new C;class Oe extends ue{constructor(t=new pe,e=new Yo){super(),this.isMesh=!0,this.type="Mesh",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),t.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=t.morphTargetInfluences.slice()),t.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},t.morphTargetDictionary)),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}updateMorphTargets(){const e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){const r=e[n[0]];if(r!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let s=0,o=r.length;s<o;s++){const a=r[s].name||String(s);this.morphTargetInfluences.push(0),this.morphTargetDictionary[a]=s}}}}getVertexPosition(t,e){const n=this.geometry,r=n.attributes.position,s=n.morphAttributes.position,o=n.morphTargetsRelative;e.fromBufferAttribute(r,t);const a=this.morphTargetInfluences;if(s&&a){Xi.set(0,0,0);for(let l=0,c=s.length;l<c;l++){const h=a[l],u=s[l];h!==0&&(Kr.fromBufferAttribute(u,t),o?Xi.addScaledVector(Kr,h):Xi.addScaledVector(Kr.sub(e),h))}e.add(Xi)}return e}raycast(t,e){const n=this.geometry,r=this.material,s=this.matrixWorld;r!==void 0&&(n.boundingSphere===null&&n.computeBoundingSphere(),Wi.copy(n.boundingSphere),Wi.applyMatrix4(s),Mn.copy(t.ray).recast(t.near),!(Wi.containsPoint(Mn.origin)===!1&&(Mn.intersectSphere(Wi,Na)===null||Mn.origin.distanceToSquared(Na)>(t.far-t.near)**2))&&(Ia.copy(s).invert(),Mn.copy(t.ray).applyMatrix4(Ia),!(n.boundingBox!==null&&Mn.intersectsBox(n.boundingBox)===!1)&&this._computeIntersections(t,e,Mn)))}_computeIntersections(t,e,n){let r;const s=this.geometry,o=this.material,a=s.index,l=s.attributes.position,c=s.attributes.uv,h=s.attributes.uv1,u=s.attributes.normal,d=s.groups,m=s.drawRange;if(a!==null)if(Array.isArray(o))for(let _=0,M=d.length;_<M;_++){const p=d[_],f=o[p.materialIndex],y=Math.max(p.start,m.start),g=Math.min(a.count,Math.min(p.start+p.count,m.start+m.count));for(let E=y,P=g;E<P;E+=3){const w=a.getX(E),b=a.getX(E+1),U=a.getX(E+2);r=$i(this,f,t,n,c,h,u,w,b,U),r&&(r.faceIndex=Math.floor(E/3),r.face.materialIndex=p.materialIndex,e.push(r))}}else{const _=Math.max(0,m.start),M=Math.min(a.count,m.start+m.count);for(let p=_,f=M;p<f;p+=3){const y=a.getX(p),g=a.getX(p+1),E=a.getX(p+2);r=$i(this,o,t,n,c,h,u,y,g,E),r&&(r.faceIndex=Math.floor(p/3),e.push(r))}}else if(l!==void 0)if(Array.isArray(o))for(let _=0,M=d.length;_<M;_++){const p=d[_],f=o[p.materialIndex],y=Math.max(p.start,m.start),g=Math.min(l.count,Math.min(p.start+p.count,m.start+m.count));for(let E=y,P=g;E<P;E+=3){const w=E,b=E+1,U=E+2;r=$i(this,f,t,n,c,h,u,w,b,U),r&&(r.faceIndex=Math.floor(E/3),r.face.materialIndex=p.materialIndex,e.push(r))}}else{const _=Math.max(0,m.start),M=Math.min(l.count,m.start+m.count);for(let p=_,f=M;p<f;p+=3){const y=p,g=p+1,E=p+2;r=$i(this,o,t,n,c,h,u,y,g,E),r&&(r.faceIndex=Math.floor(p/3),e.push(r))}}}}function rh(i,t,e,n,r,s,o,a){let l;if(t.side===Ee?l=n.intersectTriangle(o,s,r,!0,a):l=n.intersectTriangle(r,s,o,t.side===pn,a),l===null)return null;Ki.copy(a),Ki.applyMatrix4(i.matrixWorld);const c=e.ray.origin.distanceTo(Ki);return c<e.near||c>e.far?null:{distance:c,point:Ki.clone(),object:i}}function $i(i,t,e,n,r,s,o,a,l,c){i.getVertexPosition(a,Xn),i.getVertexPosition(l,qn),i.getVertexPosition(c,Yn);const h=rh(i,t,e,n,Xn,qn,Yn,Zi);if(h){r&&(qi.fromBufferAttribute(r,a),Yi.fromBufferAttribute(r,l),Ji.fromBufferAttribute(r,c),h.uv=Ve.getInterpolation(Zi,Xn,qn,Yn,qi,Yi,Ji,new it)),s&&(qi.fromBufferAttribute(s,a),Yi.fromBufferAttribute(s,l),Ji.fromBufferAttribute(s,c),h.uv1=Ve.getInterpolation(Zi,Xn,qn,Yn,qi,Yi,Ji,new it)),o&&(Fa.fromBufferAttribute(o,a),Oa.fromBufferAttribute(o,l),Ba.fromBufferAttribute(o,c),h.normal=Ve.getInterpolation(Zi,Xn,qn,Yn,Fa,Oa,Ba,new C),h.normal.dot(n.direction)>0&&h.normal.multiplyScalar(-1));const u={a,b:l,c,normal:new C,materialIndex:0};Ve.getNormal(Xn,qn,Yn,u.normal),h.face=u}return h}class Li extends pe{constructor(t=1,e=1,n=1,r=1,s=1,o=1){super(),this.type="BoxGeometry",this.parameters={width:t,height:e,depth:n,widthSegments:r,heightSegments:s,depthSegments:o};const a=this;r=Math.floor(r),s=Math.floor(s),o=Math.floor(o);const l=[],c=[],h=[],u=[];let d=0,m=0;_("z","y","x",-1,-1,n,e,t,o,s,0),_("z","y","x",1,-1,n,e,-t,o,s,1),_("x","z","y",1,1,t,n,e,r,o,2),_("x","z","y",1,-1,t,n,-e,r,o,3),_("x","y","z",1,-1,t,e,n,r,s,4),_("x","y","z",-1,-1,t,e,-n,r,s,5),this.setIndex(l),this.setAttribute("position",new qt(c,3)),this.setAttribute("normal",new qt(h,3)),this.setAttribute("uv",new qt(u,2));function _(M,p,f,y,g,E,P,w,b,U,V){const v=E/b,A=P/U,Z=E/2,K=P/2,L=w/2,k=b+1,z=U+1;let J=0,X=0;const q=new C;for(let nt=0;nt<z;nt++){const et=nt*A-K;for(let gt=0;gt<k;gt++){const Pt=gt*v-Z;q[M]=Pt*y,q[p]=et*g,q[f]=L,c.push(q.x,q.y,q.z),q[M]=0,q[p]=0,q[f]=w>0?1:-1,h.push(q.x,q.y,q.z),u.push(gt/b),u.push(1-nt/U),J+=1}}for(let nt=0;nt<U;nt++)for(let et=0;et<b;et++){const gt=d+et+k*nt,Pt=d+et+k*(nt+1),G=d+(et+1)+k*(nt+1),Q=d+(et+1)+k*nt;l.push(gt,Pt,Q),l.push(Pt,G,Q),X+=6}a.addGroup(m,X,V),m+=X,d+=J}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Li(t.width,t.height,t.depth,t.widthSegments,t.heightSegments,t.depthSegments)}}function oi(i){const t={};for(const e in i){t[e]={};for(const n in i[e]){const r=i[e][n];r&&(r.isColor||r.isMatrix3||r.isMatrix4||r.isVector2||r.isVector3||r.isVector4||r.isTexture||r.isQuaternion)?r.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),t[e][n]=null):t[e][n]=r.clone():Array.isArray(r)?t[e][n]=r.slice():t[e][n]=r}}return t}function Se(i){const t={};for(let e=0;e<i.length;e++){const n=oi(i[e]);for(const r in n)t[r]=n[r]}return t}function sh(i){const t=[];for(let e=0;e<i.length;e++)t.push(i[e].clone());return t}function Ko(i){return i.getRenderTarget()===null?i.outputColorSpace:Yt.workingColorSpace}const ah={clone:oi,merge:Se};var oh=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,lh=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;class tn extends hi{constructor(t){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=oh,this.fragmentShader=lh,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={derivatives:!1,fragDepth:!1,drawBuffers:!1,shaderTextureLOD:!1,clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,t!==void 0&&this.setValues(t)}copy(t){return super.copy(t),this.fragmentShader=t.fragmentShader,this.vertexShader=t.vertexShader,this.uniforms=oi(t.uniforms),this.uniformsGroups=sh(t.uniformsGroups),this.defines=Object.assign({},t.defines),this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.fog=t.fog,this.lights=t.lights,this.clipping=t.clipping,this.extensions=Object.assign({},t.extensions),this.glslVersion=t.glslVersion,this}toJSON(t){const e=super.toJSON(t);e.glslVersion=this.glslVersion,e.uniforms={};for(const r in this.uniforms){const o=this.uniforms[r].value;o&&o.isTexture?e.uniforms[r]={type:"t",value:o.toJSON(t).uuid}:o&&o.isColor?e.uniforms[r]={type:"c",value:o.getHex()}:o&&o.isVector2?e.uniforms[r]={type:"v2",value:o.toArray()}:o&&o.isVector3?e.uniforms[r]={type:"v3",value:o.toArray()}:o&&o.isVector4?e.uniforms[r]={type:"v4",value:o.toArray()}:o&&o.isMatrix3?e.uniforms[r]={type:"m3",value:o.toArray()}:o&&o.isMatrix4?e.uniforms[r]={type:"m4",value:o.toArray()}:e.uniforms[r]={value:o}}Object.keys(this.defines).length>0&&(e.defines=this.defines),e.vertexShader=this.vertexShader,e.fragmentShader=this.fragmentShader,e.lights=this.lights,e.clipping=this.clipping;const n={};for(const r in this.extensions)this.extensions[r]===!0&&(n[r]=!0);return Object.keys(n).length>0&&(e.extensions=n),e}}class $o extends ue{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new Jt,this.projectionMatrix=new Jt,this.projectionMatrixInverse=new Jt,this.coordinateSystem=Qe}copy(t,e){return super.copy(t,e),this.matrixWorldInverse.copy(t.matrixWorldInverse),this.projectionMatrix.copy(t.projectionMatrix),this.projectionMatrixInverse.copy(t.projectionMatrixInverse),this.coordinateSystem=t.coordinateSystem,this}getWorldDirection(t){return super.getWorldDirection(t).negate()}updateMatrixWorld(t){super.updateMatrixWorld(t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(t,e){super.updateWorldMatrix(t,e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}}const on=new C,za=new it,Ga=new it;class Pe extends $o{constructor(t=50,e=1,n=.1,r=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=t,this.zoom=1,this.near=n,this.far=r,this.focus=10,this.aspect=e,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(t,e){return super.copy(t,e),this.fov=t.fov,this.zoom=t.zoom,this.near=t.near,this.far=t.far,this.focus=t.focus,this.aspect=t.aspect,this.view=t.view===null?null:Object.assign({},t.view),this.filmGauge=t.filmGauge,this.filmOffset=t.filmOffset,this}setFocalLength(t){const e=.5*this.getFilmHeight()/t;this.fov=bi*2*Math.atan(e),this.updateProjectionMatrix()}getFocalLength(){const t=Math.tan(Si*.5*this.fov);return .5*this.getFilmHeight()/t}getEffectiveFOV(){return bi*2*Math.atan(Math.tan(Si*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(t,e,n){on.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),e.set(on.x,on.y).multiplyScalar(-t/on.z),on.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),n.set(on.x,on.y).multiplyScalar(-t/on.z)}getViewSize(t,e){return this.getViewBounds(t,za,Ga),e.subVectors(Ga,za)}setViewOffset(t,e,n,r,s,o){this.aspect=t/e,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=t,this.view.fullHeight=e,this.view.offsetX=n,this.view.offsetY=r,this.view.width=s,this.view.height=o,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const t=this.near;let e=t*Math.tan(Si*.5*this.fov)/this.zoom,n=2*e,r=this.aspect*n,s=-.5*r;const o=this.view;if(this.view!==null&&this.view.enabled){const l=o.fullWidth,c=o.fullHeight;s+=o.offsetX*r/l,e-=o.offsetY*n/c,r*=o.width/l,n*=o.height/c}const a=this.filmOffset;a!==0&&(s+=t*a/this.getFilmWidth()),this.projectionMatrix.makePerspective(s,s+r,e,e-n,t,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(t){const e=super.toJSON(t);return e.object.fov=this.fov,e.object.zoom=this.zoom,e.object.near=this.near,e.object.far=this.far,e.object.focus=this.focus,e.object.aspect=this.aspect,this.view!==null&&(e.object.view=Object.assign({},this.view)),e.object.filmGauge=this.filmGauge,e.object.filmOffset=this.filmOffset,e}}const Jn=-90,Zn=1;class ch extends ue{constructor(t,e,n){super(),this.type="CubeCamera",this.renderTarget=n,this.coordinateSystem=null,this.activeMipmapLevel=0;const r=new Pe(Jn,Zn,t,e);r.layers=this.layers,this.add(r);const s=new Pe(Jn,Zn,t,e);s.layers=this.layers,this.add(s);const o=new Pe(Jn,Zn,t,e);o.layers=this.layers,this.add(o);const a=new Pe(Jn,Zn,t,e);a.layers=this.layers,this.add(a);const l=new Pe(Jn,Zn,t,e);l.layers=this.layers,this.add(l);const c=new Pe(Jn,Zn,t,e);c.layers=this.layers,this.add(c)}updateCoordinateSystem(){const t=this.coordinateSystem,e=this.children.concat(),[n,r,s,o,a,l]=e;for(const c of e)this.remove(c);if(t===Qe)n.up.set(0,1,0),n.lookAt(1,0,0),r.up.set(0,1,0),r.lookAt(-1,0,0),s.up.set(0,0,-1),s.lookAt(0,1,0),o.up.set(0,0,1),o.lookAt(0,-1,0),a.up.set(0,1,0),a.lookAt(0,0,1),l.up.set(0,1,0),l.lookAt(0,0,-1);else if(t===fr)n.up.set(0,-1,0),n.lookAt(-1,0,0),r.up.set(0,-1,0),r.lookAt(1,0,0),s.up.set(0,0,1),s.lookAt(0,1,0),o.up.set(0,0,-1),o.lookAt(0,-1,0),a.up.set(0,-1,0),a.lookAt(0,0,1),l.up.set(0,-1,0),l.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+t);for(const c of e)this.add(c),c.updateMatrixWorld()}update(t,e){this.parent===null&&this.updateMatrixWorld();const{renderTarget:n,activeMipmapLevel:r}=this;this.coordinateSystem!==t.coordinateSystem&&(this.coordinateSystem=t.coordinateSystem,this.updateCoordinateSystem());const[s,o,a,l,c,h]=this.children,u=t.getRenderTarget(),d=t.getActiveCubeFace(),m=t.getActiveMipmapLevel(),_=t.xr.enabled;t.xr.enabled=!1;const M=n.texture.generateMipmaps;n.texture.generateMipmaps=!1,t.setRenderTarget(n,0,r),t.render(e,s),t.setRenderTarget(n,1,r),t.render(e,o),t.setRenderTarget(n,2,r),t.render(e,a),t.setRenderTarget(n,3,r),t.render(e,l),t.setRenderTarget(n,4,r),t.render(e,c),n.texture.generateMipmaps=M,t.setRenderTarget(n,5,r),t.render(e,h),t.setRenderTarget(u,d,m),t.xr.enabled=_,n.texture.needsPMREMUpdate=!0}}class jo extends ve{constructor(t,e,n,r,s,o,a,l,c,h){t=t!==void 0?t:[],e=e!==void 0?e:ri,super(t,e,n,r,s,o,a,l,c,h),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(t){this.image=t}}class hh extends Ln{constructor(t=1,e={}){super(t,t,e),this.isWebGLCubeRenderTarget=!0;const n={width:t,height:t,depth:1},r=[n,n,n,n,n,n];this.texture=new jo(r,e.mapping,e.wrapS,e.wrapT,e.magFilter,e.minFilter,e.format,e.type,e.anisotropy,e.colorSpace),this.texture.isRenderTargetTexture=!0,this.texture.generateMipmaps=e.generateMipmaps!==void 0?e.generateMipmaps:!1,this.texture.minFilter=e.minFilter!==void 0?e.minFilter:ye}fromEquirectangularTexture(t,e){this.texture.type=e.type,this.texture.colorSpace=e.colorSpace,this.texture.generateMipmaps=e.generateMipmaps,this.texture.minFilter=e.minFilter,this.texture.magFilter=e.magFilter;const n={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},r=new Li(5,5,5),s=new tn({name:"CubemapFromEquirect",uniforms:oi(n.uniforms),vertexShader:n.vertexShader,fragmentShader:n.fragmentShader,side:Ee,blending:hn});s.uniforms.tEquirect.value=e;const o=new Oe(r,s),a=e.minFilter;return e.minFilter===Rn&&(e.minFilter=ye),new ch(1,10,this).update(t,o),e.minFilter=a,o.geometry.dispose(),o.material.dispose(),this}clear(t,e,n,r){const s=t.getRenderTarget();for(let o=0;o<6;o++)t.setRenderTarget(this,o),t.clear(e,n,r);t.setRenderTarget(s)}}const $r=new C,uh=new C,fh=new Bt;class Tn{constructor(t=new C(1,0,0),e=0){this.isPlane=!0,this.normal=t,this.constant=e}set(t,e){return this.normal.copy(t),this.constant=e,this}setComponents(t,e,n,r){return this.normal.set(t,e,n),this.constant=r,this}setFromNormalAndCoplanarPoint(t,e){return this.normal.copy(t),this.constant=-e.dot(this.normal),this}setFromCoplanarPoints(t,e,n){const r=$r.subVectors(n,e).cross(uh.subVectors(t,e)).normalize();return this.setFromNormalAndCoplanarPoint(r,t),this}copy(t){return this.normal.copy(t.normal),this.constant=t.constant,this}normalize(){const t=1/this.normal.length();return this.normal.multiplyScalar(t),this.constant*=t,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(t){return this.normal.dot(t)+this.constant}distanceToSphere(t){return this.distanceToPoint(t.center)-t.radius}projectPoint(t,e){return e.copy(t).addScaledVector(this.normal,-this.distanceToPoint(t))}intersectLine(t,e){const n=t.delta($r),r=this.normal.dot(n);if(r===0)return this.distanceToPoint(t.start)===0?e.copy(t.start):null;const s=-(t.start.dot(this.normal)+this.constant)/r;return s<0||s>1?null:e.copy(t.start).addScaledVector(n,s)}intersectsLine(t){const e=this.distanceToPoint(t.start),n=this.distanceToPoint(t.end);return e<0&&n>0||n<0&&e>0}intersectsBox(t){return t.intersectsPlane(this)}intersectsSphere(t){return t.intersectsPlane(this)}coplanarPoint(t){return t.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(t,e){const n=e||fh.getNormalMatrix(t),r=this.coplanarPoint($r).applyMatrix4(t),s=this.normal.applyMatrix3(n).normalize();return this.constant=-r.dot(s),this}translate(t){return this.constant-=t.dot(this.normal),this}equals(t){return t.normal.equals(this.normal)&&t.constant===this.constant}clone(){return new this.constructor().copy(this)}}const Sn=new ci,ji=new C;class Cs{constructor(t=new Tn,e=new Tn,n=new Tn,r=new Tn,s=new Tn,o=new Tn){this.planes=[t,e,n,r,s,o]}set(t,e,n,r,s,o){const a=this.planes;return a[0].copy(t),a[1].copy(e),a[2].copy(n),a[3].copy(r),a[4].copy(s),a[5].copy(o),this}copy(t){const e=this.planes;for(let n=0;n<6;n++)e[n].copy(t.planes[n]);return this}setFromProjectionMatrix(t,e=Qe){const n=this.planes,r=t.elements,s=r[0],o=r[1],a=r[2],l=r[3],c=r[4],h=r[5],u=r[6],d=r[7],m=r[8],_=r[9],M=r[10],p=r[11],f=r[12],y=r[13],g=r[14],E=r[15];if(n[0].setComponents(l-s,d-c,p-m,E-f).normalize(),n[1].setComponents(l+s,d+c,p+m,E+f).normalize(),n[2].setComponents(l+o,d+h,p+_,E+y).normalize(),n[3].setComponents(l-o,d-h,p-_,E-y).normalize(),n[4].setComponents(l-a,d-u,p-M,E-g).normalize(),e===Qe)n[5].setComponents(l+a,d+u,p+M,E+g).normalize();else if(e===fr)n[5].setComponents(a,u,M,g).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+e);return this}intersectsObject(t){if(t.boundingSphere!==void 0)t.boundingSphere===null&&t.computeBoundingSphere(),Sn.copy(t.boundingSphere).applyMatrix4(t.matrixWorld);else{const e=t.geometry;e.boundingSphere===null&&e.computeBoundingSphere(),Sn.copy(e.boundingSphere).applyMatrix4(t.matrixWorld)}return this.intersectsSphere(Sn)}intersectsSprite(t){return Sn.center.set(0,0,0),Sn.radius=.7071067811865476,Sn.applyMatrix4(t.matrixWorld),this.intersectsSphere(Sn)}intersectsSphere(t){const e=this.planes,n=t.center,r=-t.radius;for(let s=0;s<6;s++)if(e[s].distanceToPoint(n)<r)return!1;return!0}intersectsBox(t){const e=this.planes;for(let n=0;n<6;n++){const r=e[n];if(ji.x=r.normal.x>0?t.max.x:t.min.x,ji.y=r.normal.y>0?t.max.y:t.min.y,ji.z=r.normal.z>0?t.max.z:t.min.z,r.distanceToPoint(ji)<0)return!1}return!0}containsPoint(t){const e=this.planes;for(let n=0;n<6;n++)if(e[n].distanceToPoint(t)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}}function Qo(){let i=null,t=!1,e=null,n=null;function r(s,o){e(s,o),n=i.requestAnimationFrame(r)}return{start:function(){t!==!0&&e!==null&&(n=i.requestAnimationFrame(r),t=!0)},stop:function(){i.cancelAnimationFrame(n),t=!1},setAnimationLoop:function(s){e=s},setContext:function(s){i=s}}}function dh(i,t){const e=t.isWebGL2,n=new WeakMap;function r(c,h){const u=c.array,d=c.usage,m=u.byteLength,_=i.createBuffer();i.bindBuffer(h,_),i.bufferData(h,u,d),c.onUploadCallback();let M;if(u instanceof Float32Array)M=i.FLOAT;else if(u instanceof Uint16Array)if(c.isFloat16BufferAttribute)if(e)M=i.HALF_FLOAT;else throw new Error("THREE.WebGLAttributes: Usage of Float16BufferAttribute requires WebGL2.");else M=i.UNSIGNED_SHORT;else if(u instanceof Int16Array)M=i.SHORT;else if(u instanceof Uint32Array)M=i.UNSIGNED_INT;else if(u instanceof Int32Array)M=i.INT;else if(u instanceof Int8Array)M=i.BYTE;else if(u instanceof Uint8Array)M=i.UNSIGNED_BYTE;else if(u instanceof Uint8ClampedArray)M=i.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+u);return{buffer:_,type:M,bytesPerElement:u.BYTES_PER_ELEMENT,version:c.version,size:m}}function s(c,h,u){const d=h.array,m=h._updateRange,_=h.updateRanges;if(i.bindBuffer(u,c),m.count===-1&&_.length===0&&i.bufferSubData(u,0,d),_.length!==0){for(let M=0,p=_.length;M<p;M++){const f=_[M];e?i.bufferSubData(u,f.start*d.BYTES_PER_ELEMENT,d,f.start,f.count):i.bufferSubData(u,f.start*d.BYTES_PER_ELEMENT,d.subarray(f.start,f.start+f.count))}h.clearUpdateRanges()}m.count!==-1&&(e?i.bufferSubData(u,m.offset*d.BYTES_PER_ELEMENT,d,m.offset,m.count):i.bufferSubData(u,m.offset*d.BYTES_PER_ELEMENT,d.subarray(m.offset,m.offset+m.count)),m.count=-1),h.onUploadCallback()}function o(c){return c.isInterleavedBufferAttribute&&(c=c.data),n.get(c)}function a(c){c.isInterleavedBufferAttribute&&(c=c.data);const h=n.get(c);h&&(i.deleteBuffer(h.buffer),n.delete(c))}function l(c,h){if(c.isGLBufferAttribute){const d=n.get(c);(!d||d.version<c.version)&&n.set(c,{buffer:c.buffer,type:c.type,bytesPerElement:c.elementSize,version:c.version});return}c.isInterleavedBufferAttribute&&(c=c.data);const u=n.get(c);if(u===void 0)n.set(c,r(c,h));else if(u.version<c.version){if(u.size!==c.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");s(u.buffer,c,h),u.version=c.version}}return{get:o,remove:a,update:l}}class _r extends pe{constructor(t=1,e=1,n=1,r=1){super(),this.type="PlaneGeometry",this.parameters={width:t,height:e,widthSegments:n,heightSegments:r};const s=t/2,o=e/2,a=Math.floor(n),l=Math.floor(r),c=a+1,h=l+1,u=t/a,d=e/l,m=[],_=[],M=[],p=[];for(let f=0;f<h;f++){const y=f*d-o;for(let g=0;g<c;g++){const E=g*u-s;_.push(E,-y,0),M.push(0,0,1),p.push(g/a),p.push(1-f/l)}}for(let f=0;f<l;f++)for(let y=0;y<a;y++){const g=y+c*f,E=y+c*(f+1),P=y+1+c*(f+1),w=y+1+c*f;m.push(g,E,w),m.push(E,P,w)}this.setIndex(m),this.setAttribute("position",new qt(_,3)),this.setAttribute("normal",new qt(M,3)),this.setAttribute("uv",new qt(p,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new _r(t.width,t.height,t.widthSegments,t.heightSegments)}}var ph=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,mh=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,gh=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,_h=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,vh=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,xh=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,Mh=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,Sh=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,yh=`#ifdef USE_BATCHING
	attribute float batchId;
	uniform highp sampler2D batchingTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,Eh=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( batchId );
#endif`,Th=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,Ah=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,bh=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,wh=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,Rh=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,Ch=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,Ph=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,Lh=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,Dh=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,Uh=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,Ih=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,Nh=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR )
	varying vec3 vColor;
#endif`,Fh=`#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif`,Oh=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
mat3 transposeMat3( const in mat3 m ) {
	mat3 tmp;
	tmp[ 0 ] = vec3( m[ 0 ].x, m[ 1 ].x, m[ 2 ].x );
	tmp[ 1 ] = vec3( m[ 0 ].y, m[ 1 ].y, m[ 2 ].y );
	tmp[ 2 ] = vec3( m[ 0 ].z, m[ 1 ].z, m[ 2 ].z );
	return tmp;
}
float luminance( const in vec3 rgb ) {
	const vec3 weights = vec3( 0.2126729, 0.7151522, 0.0721750 );
	return dot( weights, rgb );
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,Bh=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,zh=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,Gh=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,Hh=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,Vh=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,kh=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,Wh="gl_FragColor = linearToOutputTexel( gl_FragColor );",Xh=`
const mat3 LINEAR_SRGB_TO_LINEAR_DISPLAY_P3 = mat3(
	vec3( 0.8224621, 0.177538, 0.0 ),
	vec3( 0.0331941, 0.9668058, 0.0 ),
	vec3( 0.0170827, 0.0723974, 0.9105199 )
);
const mat3 LINEAR_DISPLAY_P3_TO_LINEAR_SRGB = mat3(
	vec3( 1.2249401, - 0.2249404, 0.0 ),
	vec3( - 0.0420569, 1.0420571, 0.0 ),
	vec3( - 0.0196376, - 0.0786361, 1.0982735 )
);
vec4 LinearSRGBToLinearDisplayP3( in vec4 value ) {
	return vec4( value.rgb * LINEAR_SRGB_TO_LINEAR_DISPLAY_P3, value.a );
}
vec4 LinearDisplayP3ToLinearSRGB( in vec4 value ) {
	return vec4( value.rgb * LINEAR_DISPLAY_P3_TO_LINEAR_SRGB, value.a );
}
vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}
vec4 LinearToLinear( in vec4 value ) {
	return value;
}
vec4 LinearTosRGB( in vec4 value ) {
	return sRGBTransferOETF( value );
}`,qh=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`,Yh=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,Jh=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,Zh=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,Kh=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,$h=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,jh=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,Qh=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,tu=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,eu=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,nu=`#ifdef USE_LIGHTMAP
	vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
	vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
	reflectedLight.indirectDiffuse += lightMapIrradiance;
#endif`,iu=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,ru=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,su=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,au=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	#if defined ( LEGACY_LIGHTS )
		if ( cutoffDistance > 0.0 && decayExponent > 0.0 ) {
			return pow( saturate( - lightDistance / cutoffDistance + 1.0 ), decayExponent );
		}
		return 1.0;
	#else
		float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
		if ( cutoffDistance > 0.0 ) {
			distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
		}
		return distanceFalloff;
	#endif
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,ou=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, roughness * roughness) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,lu=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,cu=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,hu=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,uu=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,fu=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb * ( 1.0 - metalnessFactor );
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = mix( min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = mix( vec3( 0.04 ), diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.07, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,du=`struct PhysicalMaterial {
	vec3 diffuseColor;
	float roughness;
	vec3 specularColor;
	float specularF90;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return saturate(v);
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColor;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transposeMat3( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float a = roughness < 0.25 ? -339.2 * r2 + 161.4 * roughness - 25.9 : -8.48 * r2 + 14.3 * roughness - 9.95;
	float b = roughness < 0.25 ? 44.0 * r2 - 23.7 * roughness + 3.26 : 1.97 * r2 - 3.27 * roughness + 0.72;
	float DG = exp( a * dotNV + b ) + ( roughness < 0.25 ? 0.0 : 0.1 * ( roughness - 0.25 ) );
	return saturate( DG * RECIPROCAL_PI );
}
vec2 DFGApprox( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	const vec4 c0 = vec4( - 1, - 0.0275, - 0.572, 0.022 );
	const vec4 c1 = vec4( 1, 0.0425, 1.04, - 0.04 );
	vec4 r = roughness * c0 + c1;
	float a004 = min( r.x * r.x, exp2( - 9.28 * dotNV ) ) * r.x + r.y;
	vec2 fab = vec2( - 1.04, 1.04 ) * a004 + r.zw;
	return fab;
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColor * t2.x + ( vec3( 1.0 ) - material.specularColor ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseColor * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
	#endif
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnel, material.roughness, singleScattering, multiScattering );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScattering, multiScattering );
	#endif
	vec3 totalScattering = singleScattering + multiScattering;
	vec3 diffuse = material.diffuseColor * ( 1.0 - max( max( totalScattering.r, totalScattering.g ), totalScattering.b ) );
	reflectedLight.indirectSpecular += radiance * singleScattering;
	reflectedLight.indirectSpecular += multiScattering * cosineWeightedIrradiance;
	reflectedLight.indirectDiffuse += diffuse * cosineWeightedIrradiance;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,pu=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnel = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,mu=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,gu=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,_u=`#if defined( USE_LOGDEPTHBUF ) && defined( USE_LOGDEPTHBUF_EXT )
	gl_FragDepthEXT = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,vu=`#if defined( USE_LOGDEPTHBUF ) && defined( USE_LOGDEPTHBUF_EXT )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,xu=`#ifdef USE_LOGDEPTHBUF
	#ifdef USE_LOGDEPTHBUF_EXT
		varying float vFragDepth;
		varying float vIsPerspective;
	#else
		uniform float logDepthBufFC;
	#endif
#endif`,Mu=`#ifdef USE_LOGDEPTHBUF
	#ifdef USE_LOGDEPTHBUF_EXT
		vFragDepth = 1.0 + gl_Position.w;
		vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
	#else
		if ( isPerspectiveMatrix( projectionMatrix ) ) {
			gl_Position.z = log2( max( EPSILON, gl_Position.w + 1.0 ) ) * logDepthBufFC - 1.0;
			gl_Position.z *= gl_Position.w;
		}
	#endif
#endif`,Su=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = vec4( mix( pow( sampledDiffuseColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), sampledDiffuseColor.rgb * 0.0773993808, vec3( lessThanEqual( sampledDiffuseColor.rgb, vec3( 0.04045 ) ) ) ), sampledDiffuseColor.w );
	
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,yu=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,Eu=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,Tu=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,Au=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,bu=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,wu=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[MORPHTARGETS_COUNT];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,Ru=`#if defined( USE_MORPHCOLORS ) && defined( MORPHTARGETS_TEXTURE )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,Cu=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	#ifdef MORPHTARGETS_TEXTURE
		for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
			if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
		}
	#else
		objectNormal += morphNormal0 * morphTargetInfluences[ 0 ];
		objectNormal += morphNormal1 * morphTargetInfluences[ 1 ];
		objectNormal += morphNormal2 * morphTargetInfluences[ 2 ];
		objectNormal += morphNormal3 * morphTargetInfluences[ 3 ];
	#endif
#endif`,Pu=`#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
	#endif
	#ifdef MORPHTARGETS_TEXTURE
		#ifndef USE_INSTANCING_MORPH
			uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
		#endif
		uniform sampler2DArray morphTargetsTexture;
		uniform ivec2 morphTargetsTextureSize;
		vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
			int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
			int y = texelIndex / morphTargetsTextureSize.x;
			int x = texelIndex - y * morphTargetsTextureSize.x;
			ivec3 morphUV = ivec3( x, y, morphTargetIndex );
			return texelFetch( morphTargetsTexture, morphUV, 0 );
		}
	#else
		#ifndef USE_MORPHNORMALS
			uniform float morphTargetInfluences[ 8 ];
		#else
			uniform float morphTargetInfluences[ 4 ];
		#endif
	#endif
#endif`,Lu=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	#ifdef MORPHTARGETS_TEXTURE
		for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
			if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
		}
	#else
		transformed += morphTarget0 * morphTargetInfluences[ 0 ];
		transformed += morphTarget1 * morphTargetInfluences[ 1 ];
		transformed += morphTarget2 * morphTargetInfluences[ 2 ];
		transformed += morphTarget3 * morphTargetInfluences[ 3 ];
		#ifndef USE_MORPHNORMALS
			transformed += morphTarget4 * morphTargetInfluences[ 4 ];
			transformed += morphTarget5 * morphTargetInfluences[ 5 ];
			transformed += morphTarget6 * morphTargetInfluences[ 6 ];
			transformed += morphTarget7 * morphTargetInfluences[ 7 ];
		#endif
	#endif
#endif`,Du=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,Uu=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,Iu=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Nu=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Fu=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,Ou=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,Bu=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,zu=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,Gu=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,Hu=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,Vu=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,ku=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;
const vec3 PackFactors = vec3( 256. * 256. * 256., 256. * 256., 256. );
const vec4 UnpackFactors = UnpackDownscale / vec4( PackFactors, 1. );
const float ShiftRight8 = 1. / 256.;
vec4 packDepthToRGBA( const in float v ) {
	vec4 r = vec4( fract( v * PackFactors ), v );
	r.yzw -= r.xyz * ShiftRight8;	return r * PackUpscale;
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors );
}
vec2 packDepthToRG( in highp float v ) {
	return packDepthToRGBA( v ).yx;
}
float unpackRGToDepth( const in highp vec2 v ) {
	return unpackRGBAToDepth( vec4( v.xy, 0.0, 0.0 ) );
}
vec4 pack2HalfToRGBA( vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`,Wu=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,Xu=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,qu=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,Yu=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,Ju=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,Zu=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,Ku=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		struct SpotLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform sampler2D pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	float texture2DCompare( sampler2D depths, vec2 uv, float compare ) {
		return step( compare, unpackRGBAToDepth( texture2D( depths, uv ) ) );
	}
	vec2 texture2DDistribution( sampler2D shadow, vec2 uv ) {
		return unpackRGBATo2Half( texture2D( shadow, uv ) );
	}
	float VSMShadow (sampler2D shadow, vec2 uv, float compare ){
		float occlusion = 1.0;
		vec2 distribution = texture2DDistribution( shadow, uv );
		float hard_shadow = step( compare , distribution.x );
		if (hard_shadow != 1.0 ) {
			float distance = compare - distribution.x ;
			float variance = max( 0.00000, distribution.y * distribution.y );
			float softness_probability = variance / (variance + distance * distance );			softness_probability = clamp( ( softness_probability - 0.3 ) / ( 0.95 - 0.3 ), 0.0, 1.0 );			occlusion = clamp( max( hard_shadow, softness_probability ), 0.0, 1.0 );
		}
		return occlusion;
	}
	float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
		float shadow = 1.0;
		shadowCoord.xyz /= shadowCoord.w;
		shadowCoord.z += shadowBias;
		bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
		bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
		if ( frustumTest ) {
		#if defined( SHADOWMAP_TYPE_PCF )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx0 = - texelSize.x * shadowRadius;
			float dy0 = - texelSize.y * shadowRadius;
			float dx1 = + texelSize.x * shadowRadius;
			float dy1 = + texelSize.y * shadowRadius;
			float dx2 = dx0 / 2.0;
			float dy2 = dy0 / 2.0;
			float dx3 = dx1 / 2.0;
			float dy3 = dy1 / 2.0;
			shadow = (
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy1 ), shadowCoord.z )
			) * ( 1.0 / 17.0 );
		#elif defined( SHADOWMAP_TYPE_PCF_SOFT )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx = texelSize.x;
			float dy = texelSize.y;
			vec2 uv = shadowCoord.xy;
			vec2 f = fract( uv * shadowMapSize + 0.5 );
			uv -= f * texelSize;
			shadow = (
				texture2DCompare( shadowMap, uv, shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( dx, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( 0.0, dy ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + texelSize, shadowCoord.z ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, 0.0 ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 0.0 ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, dy ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( 0.0, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 0.0, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( texture2DCompare( shadowMap, uv + vec2( dx, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( dx, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( mix( texture2DCompare( shadowMap, uv + vec2( -dx, -dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, -dy ), shadowCoord.z ),
						  f.x ),
					 mix( texture2DCompare( shadowMap, uv + vec2( -dx, 2.0 * dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 2.0 * dy ), shadowCoord.z ),
						  f.x ),
					 f.y )
			) * ( 1.0 / 9.0 );
		#elif defined( SHADOWMAP_TYPE_VSM )
			shadow = VSMShadow( shadowMap, shadowCoord.xy, shadowCoord.z );
		#else
			shadow = texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z );
		#endif
		}
		return shadow;
	}
	vec2 cubeToUV( vec3 v, float texelSizeY ) {
		vec3 absV = abs( v );
		float scaleToCube = 1.0 / max( absV.x, max( absV.y, absV.z ) );
		absV *= scaleToCube;
		v *= scaleToCube * ( 1.0 - 2.0 * texelSizeY );
		vec2 planar = v.xy;
		float almostATexel = 1.5 * texelSizeY;
		float almostOne = 1.0 - almostATexel;
		if ( absV.z >= almostOne ) {
			if ( v.z > 0.0 )
				planar.x = 4.0 - v.x;
		} else if ( absV.x >= almostOne ) {
			float signX = sign( v.x );
			planar.x = v.z * signX + 2.0 * signX;
		} else if ( absV.y >= almostOne ) {
			float signY = sign( v.y );
			planar.x = v.x + 2.0 * signY + 2.0;
			planar.y = v.z * signY - 2.0;
		}
		return vec2( 0.125, 0.25 ) * planar + vec2( 0.375, 0.75 );
	}
	float getPointShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		vec2 texelSize = vec2( 1.0 ) / ( shadowMapSize * vec2( 4.0, 2.0 ) );
		vec3 lightToPosition = shadowCoord.xyz;
		float dp = ( length( lightToPosition ) - shadowCameraNear ) / ( shadowCameraFar - shadowCameraNear );		dp += shadowBias;
		vec3 bd3D = normalize( lightToPosition );
		#if defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_PCF_SOFT ) || defined( SHADOWMAP_TYPE_VSM )
			vec2 offset = vec2( - 1, 1 ) * shadowRadius * texelSize.y;
			return (
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyy, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyy, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyx, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyx, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxy, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxy, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxx, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxx, texelSize.y ), dp )
			) * ( 1.0 / 9.0 );
		#else
			return texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp );
		#endif
	}
#endif`,$u=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,ju=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,Qu=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,tf=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,ef=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,nf=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,rf=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,sf=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,af=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,of=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,lf=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 OptimizedCineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	float startCompression = 0.8 - 0.04;
	float desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min(color.r, min(color.g, color.b));
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max(color.r, max(color.g, color.b));
	if (peak < startCompression) return color;
	float d = 1. - startCompression;
	float newPeak = 1. - d * d / (peak + d - startCompression);
	color *= newPeak / peak;
	float g = 1. - 1. / (desaturation * (peak - newPeak) + 1.);
	return mix(color, vec3(1, 1, 1), g);
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,cf=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseColor, material.specularColor, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,hf=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
		vec3 refractedRayExit = position + transmissionRay;
		vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
		vec2 refractionCoords = ndcPos.xy / ndcPos.w;
		refractionCoords += 1.0;
		refractionCoords /= 2.0;
		vec4 transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
		vec3 transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,uf=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,ff=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,df=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,pf=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;const mf=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,gf=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,_f=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,vf=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,xf=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,Mf=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,Sf=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,yf=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	float fragCoordZ = 0.5 * vHighPrecisionZW[0] / vHighPrecisionZW[1] + 0.5;
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#endif
}`,Ef=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,Tf=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = packDepthToRGBA( dist );
}`,Af=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,bf=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,wf=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,Rf=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,Cf=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,Pf=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,Lf=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,Df=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,Uf=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,If=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,Nf=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,Ff=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <packing>
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( packNormalToRGB( normal ), diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,Of=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,Bf=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,zf=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,Gf=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
		float sheenEnergyComp = 1.0 - 0.157 * max3( material.sheenColor );
		outgoingLight = outgoingLight * sheenEnergyComp + sheenSpecularDirect + sheenSpecularIndirect;
	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,Hf=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,Vf=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,kf=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,Wf=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,Xf=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,qf=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,Yf=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix * vec4( 0.0, 0.0, 0.0, 1.0 );
	vec2 scale;
	scale.x = length( vec3( modelMatrix[ 0 ].x, modelMatrix[ 0 ].y, modelMatrix[ 0 ].z ) );
	scale.y = length( vec3( modelMatrix[ 1 ].x, modelMatrix[ 1 ].y, modelMatrix[ 1 ].z ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,Jf=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,Ot={alphahash_fragment:ph,alphahash_pars_fragment:mh,alphamap_fragment:gh,alphamap_pars_fragment:_h,alphatest_fragment:vh,alphatest_pars_fragment:xh,aomap_fragment:Mh,aomap_pars_fragment:Sh,batching_pars_vertex:yh,batching_vertex:Eh,begin_vertex:Th,beginnormal_vertex:Ah,bsdfs:bh,iridescence_fragment:wh,bumpmap_pars_fragment:Rh,clipping_planes_fragment:Ch,clipping_planes_pars_fragment:Ph,clipping_planes_pars_vertex:Lh,clipping_planes_vertex:Dh,color_fragment:Uh,color_pars_fragment:Ih,color_pars_vertex:Nh,color_vertex:Fh,common:Oh,cube_uv_reflection_fragment:Bh,defaultnormal_vertex:zh,displacementmap_pars_vertex:Gh,displacementmap_vertex:Hh,emissivemap_fragment:Vh,emissivemap_pars_fragment:kh,colorspace_fragment:Wh,colorspace_pars_fragment:Xh,envmap_fragment:qh,envmap_common_pars_fragment:Yh,envmap_pars_fragment:Jh,envmap_pars_vertex:Zh,envmap_physical_pars_fragment:ou,envmap_vertex:Kh,fog_vertex:$h,fog_pars_vertex:jh,fog_fragment:Qh,fog_pars_fragment:tu,gradientmap_pars_fragment:eu,lightmap_fragment:nu,lightmap_pars_fragment:iu,lights_lambert_fragment:ru,lights_lambert_pars_fragment:su,lights_pars_begin:au,lights_toon_fragment:lu,lights_toon_pars_fragment:cu,lights_phong_fragment:hu,lights_phong_pars_fragment:uu,lights_physical_fragment:fu,lights_physical_pars_fragment:du,lights_fragment_begin:pu,lights_fragment_maps:mu,lights_fragment_end:gu,logdepthbuf_fragment:_u,logdepthbuf_pars_fragment:vu,logdepthbuf_pars_vertex:xu,logdepthbuf_vertex:Mu,map_fragment:Su,map_pars_fragment:yu,map_particle_fragment:Eu,map_particle_pars_fragment:Tu,metalnessmap_fragment:Au,metalnessmap_pars_fragment:bu,morphinstance_vertex:wu,morphcolor_vertex:Ru,morphnormal_vertex:Cu,morphtarget_pars_vertex:Pu,morphtarget_vertex:Lu,normal_fragment_begin:Du,normal_fragment_maps:Uu,normal_pars_fragment:Iu,normal_pars_vertex:Nu,normal_vertex:Fu,normalmap_pars_fragment:Ou,clearcoat_normal_fragment_begin:Bu,clearcoat_normal_fragment_maps:zu,clearcoat_pars_fragment:Gu,iridescence_pars_fragment:Hu,opaque_fragment:Vu,packing:ku,premultiplied_alpha_fragment:Wu,project_vertex:Xu,dithering_fragment:qu,dithering_pars_fragment:Yu,roughnessmap_fragment:Ju,roughnessmap_pars_fragment:Zu,shadowmap_pars_fragment:Ku,shadowmap_pars_vertex:$u,shadowmap_vertex:ju,shadowmask_pars_fragment:Qu,skinbase_vertex:tf,skinning_pars_vertex:ef,skinning_vertex:nf,skinnormal_vertex:rf,specularmap_fragment:sf,specularmap_pars_fragment:af,tonemapping_fragment:of,tonemapping_pars_fragment:lf,transmission_fragment:cf,transmission_pars_fragment:hf,uv_pars_fragment:uf,uv_pars_vertex:ff,uv_vertex:df,worldpos_vertex:pf,background_vert:mf,background_frag:gf,backgroundCube_vert:_f,backgroundCube_frag:vf,cube_vert:xf,cube_frag:Mf,depth_vert:Sf,depth_frag:yf,distanceRGBA_vert:Ef,distanceRGBA_frag:Tf,equirect_vert:Af,equirect_frag:bf,linedashed_vert:wf,linedashed_frag:Rf,meshbasic_vert:Cf,meshbasic_frag:Pf,meshlambert_vert:Lf,meshlambert_frag:Df,meshmatcap_vert:Uf,meshmatcap_frag:If,meshnormal_vert:Nf,meshnormal_frag:Ff,meshphong_vert:Of,meshphong_frag:Bf,meshphysical_vert:zf,meshphysical_frag:Gf,meshtoon_vert:Hf,meshtoon_frag:Vf,points_vert:kf,points_frag:Wf,shadow_vert:Xf,shadow_frag:qf,sprite_vert:Yf,sprite_frag:Jf},ct={common:{diffuse:{value:new zt(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new Bt},alphaMap:{value:null},alphaMapTransform:{value:new Bt},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new Bt}},envmap:{envMap:{value:null},envMapRotation:{value:new Bt},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new Bt}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new Bt}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new Bt},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new Bt},normalScale:{value:new it(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new Bt},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new Bt}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new Bt}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new Bt}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new zt(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new zt(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new Bt},alphaTest:{value:0},uvTransform:{value:new Bt}},sprite:{diffuse:{value:new zt(16777215)},opacity:{value:1},center:{value:new it(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new Bt},alphaMap:{value:null},alphaMapTransform:{value:new Bt},alphaTest:{value:0}}},Ge={basic:{uniforms:Se([ct.common,ct.specularmap,ct.envmap,ct.aomap,ct.lightmap,ct.fog]),vertexShader:Ot.meshbasic_vert,fragmentShader:Ot.meshbasic_frag},lambert:{uniforms:Se([ct.common,ct.specularmap,ct.envmap,ct.aomap,ct.lightmap,ct.emissivemap,ct.bumpmap,ct.normalmap,ct.displacementmap,ct.fog,ct.lights,{emissive:{value:new zt(0)}}]),vertexShader:Ot.meshlambert_vert,fragmentShader:Ot.meshlambert_frag},phong:{uniforms:Se([ct.common,ct.specularmap,ct.envmap,ct.aomap,ct.lightmap,ct.emissivemap,ct.bumpmap,ct.normalmap,ct.displacementmap,ct.fog,ct.lights,{emissive:{value:new zt(0)},specular:{value:new zt(1118481)},shininess:{value:30}}]),vertexShader:Ot.meshphong_vert,fragmentShader:Ot.meshphong_frag},standard:{uniforms:Se([ct.common,ct.envmap,ct.aomap,ct.lightmap,ct.emissivemap,ct.bumpmap,ct.normalmap,ct.displacementmap,ct.roughnessmap,ct.metalnessmap,ct.fog,ct.lights,{emissive:{value:new zt(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:Ot.meshphysical_vert,fragmentShader:Ot.meshphysical_frag},toon:{uniforms:Se([ct.common,ct.aomap,ct.lightmap,ct.emissivemap,ct.bumpmap,ct.normalmap,ct.displacementmap,ct.gradientmap,ct.fog,ct.lights,{emissive:{value:new zt(0)}}]),vertexShader:Ot.meshtoon_vert,fragmentShader:Ot.meshtoon_frag},matcap:{uniforms:Se([ct.common,ct.bumpmap,ct.normalmap,ct.displacementmap,ct.fog,{matcap:{value:null}}]),vertexShader:Ot.meshmatcap_vert,fragmentShader:Ot.meshmatcap_frag},points:{uniforms:Se([ct.points,ct.fog]),vertexShader:Ot.points_vert,fragmentShader:Ot.points_frag},dashed:{uniforms:Se([ct.common,ct.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:Ot.linedashed_vert,fragmentShader:Ot.linedashed_frag},depth:{uniforms:Se([ct.common,ct.displacementmap]),vertexShader:Ot.depth_vert,fragmentShader:Ot.depth_frag},normal:{uniforms:Se([ct.common,ct.bumpmap,ct.normalmap,ct.displacementmap,{opacity:{value:1}}]),vertexShader:Ot.meshnormal_vert,fragmentShader:Ot.meshnormal_frag},sprite:{uniforms:Se([ct.sprite,ct.fog]),vertexShader:Ot.sprite_vert,fragmentShader:Ot.sprite_frag},background:{uniforms:{uvTransform:{value:new Bt},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:Ot.background_vert,fragmentShader:Ot.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new Bt}},vertexShader:Ot.backgroundCube_vert,fragmentShader:Ot.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:Ot.cube_vert,fragmentShader:Ot.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:Ot.equirect_vert,fragmentShader:Ot.equirect_frag},distanceRGBA:{uniforms:Se([ct.common,ct.displacementmap,{referencePosition:{value:new C},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:Ot.distanceRGBA_vert,fragmentShader:Ot.distanceRGBA_frag},shadow:{uniforms:Se([ct.lights,ct.fog,{color:{value:new zt(0)},opacity:{value:1}}]),vertexShader:Ot.shadow_vert,fragmentShader:Ot.shadow_frag}};Ge.physical={uniforms:Se([Ge.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new Bt},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new Bt},clearcoatNormalScale:{value:new it(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new Bt},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new Bt},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new Bt},sheen:{value:0},sheenColor:{value:new zt(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new Bt},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new Bt},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new Bt},transmissionSamplerSize:{value:new it},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new Bt},attenuationDistance:{value:0},attenuationColor:{value:new zt(0)},specularColor:{value:new zt(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new Bt},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new Bt},anisotropyVector:{value:new it},anisotropyMap:{value:null},anisotropyMapTransform:{value:new Bt}}]),vertexShader:Ot.meshphysical_vert,fragmentShader:Ot.meshphysical_frag};const Qi={r:0,b:0,g:0},yn=new ke,Zf=new Jt;function Kf(i,t,e,n,r,s,o){const a=new zt(0);let l=s===!0?0:1,c,h,u=null,d=0,m=null;function _(p,f){let y=!1,g=f.isScene===!0?f.background:null;g&&g.isTexture&&(g=(f.backgroundBlurriness>0?e:t).get(g)),g===null?M(a,l):g&&g.isColor&&(M(g,1),y=!0);const E=i.xr.getEnvironmentBlendMode();E==="additive"?n.buffers.color.setClear(0,0,0,1,o):E==="alpha-blend"&&n.buffers.color.setClear(0,0,0,0,o),(i.autoClear||y)&&i.clear(i.autoClearColor,i.autoClearDepth,i.autoClearStencil),g&&(g.isCubeTexture||g.mapping===mr)?(h===void 0&&(h=new Oe(new Li(1,1,1),new tn({name:"BackgroundCubeMaterial",uniforms:oi(Ge.backgroundCube.uniforms),vertexShader:Ge.backgroundCube.vertexShader,fragmentShader:Ge.backgroundCube.fragmentShader,side:Ee,depthTest:!1,depthWrite:!1,fog:!1})),h.geometry.deleteAttribute("normal"),h.geometry.deleteAttribute("uv"),h.onBeforeRender=function(P,w,b){this.matrixWorld.copyPosition(b.matrixWorld)},Object.defineProperty(h.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),r.update(h)),yn.copy(f.backgroundRotation),yn.x*=-1,yn.y*=-1,yn.z*=-1,g.isCubeTexture&&g.isRenderTargetTexture===!1&&(yn.y*=-1,yn.z*=-1),h.material.uniforms.envMap.value=g,h.material.uniforms.flipEnvMap.value=g.isCubeTexture&&g.isRenderTargetTexture===!1?-1:1,h.material.uniforms.backgroundBlurriness.value=f.backgroundBlurriness,h.material.uniforms.backgroundIntensity.value=f.backgroundIntensity,h.material.uniforms.backgroundRotation.value.setFromMatrix4(Zf.makeRotationFromEuler(yn)),h.material.toneMapped=Yt.getTransfer(g.colorSpace)!==$t,(u!==g||d!==g.version||m!==i.toneMapping)&&(h.material.needsUpdate=!0,u=g,d=g.version,m=i.toneMapping),h.layers.enableAll(),p.unshift(h,h.geometry,h.material,0,0,null)):g&&g.isTexture&&(c===void 0&&(c=new Oe(new _r(2,2),new tn({name:"BackgroundMaterial",uniforms:oi(Ge.background.uniforms),vertexShader:Ge.background.vertexShader,fragmentShader:Ge.background.fragmentShader,side:pn,depthTest:!1,depthWrite:!1,fog:!1})),c.geometry.deleteAttribute("normal"),Object.defineProperty(c.material,"map",{get:function(){return this.uniforms.t2D.value}}),r.update(c)),c.material.uniforms.t2D.value=g,c.material.uniforms.backgroundIntensity.value=f.backgroundIntensity,c.material.toneMapped=Yt.getTransfer(g.colorSpace)!==$t,g.matrixAutoUpdate===!0&&g.updateMatrix(),c.material.uniforms.uvTransform.value.copy(g.matrix),(u!==g||d!==g.version||m!==i.toneMapping)&&(c.material.needsUpdate=!0,u=g,d=g.version,m=i.toneMapping),c.layers.enableAll(),p.unshift(c,c.geometry,c.material,0,0,null))}function M(p,f){p.getRGB(Qi,Ko(i)),n.buffers.color.setClear(Qi.r,Qi.g,Qi.b,f,o)}return{getClearColor:function(){return a},setClearColor:function(p,f=1){a.set(p),l=f,M(a,l)},getClearAlpha:function(){return l},setClearAlpha:function(p){l=p,M(a,l)},render:_}}function $f(i,t,e,n){const r=i.getParameter(i.MAX_VERTEX_ATTRIBS),s=n.isWebGL2?null:t.get("OES_vertex_array_object"),o=n.isWebGL2||s!==null,a={},l=p(null);let c=l,h=!1;function u(L,k,z,J,X){let q=!1;if(o){const nt=M(J,z,k);c!==nt&&(c=nt,m(c.object)),q=f(L,J,z,X),q&&y(L,J,z,X)}else{const nt=k.wireframe===!0;(c.geometry!==J.id||c.program!==z.id||c.wireframe!==nt)&&(c.geometry=J.id,c.program=z.id,c.wireframe=nt,q=!0)}X!==null&&e.update(X,i.ELEMENT_ARRAY_BUFFER),(q||h)&&(h=!1,U(L,k,z,J),X!==null&&i.bindBuffer(i.ELEMENT_ARRAY_BUFFER,e.get(X).buffer))}function d(){return n.isWebGL2?i.createVertexArray():s.createVertexArrayOES()}function m(L){return n.isWebGL2?i.bindVertexArray(L):s.bindVertexArrayOES(L)}function _(L){return n.isWebGL2?i.deleteVertexArray(L):s.deleteVertexArrayOES(L)}function M(L,k,z){const J=z.wireframe===!0;let X=a[L.id];X===void 0&&(X={},a[L.id]=X);let q=X[k.id];q===void 0&&(q={},X[k.id]=q);let nt=q[J];return nt===void 0&&(nt=p(d()),q[J]=nt),nt}function p(L){const k=[],z=[],J=[];for(let X=0;X<r;X++)k[X]=0,z[X]=0,J[X]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:k,enabledAttributes:z,attributeDivisors:J,object:L,attributes:{},index:null}}function f(L,k,z,J){const X=c.attributes,q=k.attributes;let nt=0;const et=z.getAttributes();for(const gt in et)if(et[gt].location>=0){const G=X[gt];let Q=q[gt];if(Q===void 0&&(gt==="instanceMatrix"&&L.instanceMatrix&&(Q=L.instanceMatrix),gt==="instanceColor"&&L.instanceColor&&(Q=L.instanceColor)),G===void 0||G.attribute!==Q||Q&&G.data!==Q.data)return!0;nt++}return c.attributesNum!==nt||c.index!==J}function y(L,k,z,J){const X={},q=k.attributes;let nt=0;const et=z.getAttributes();for(const gt in et)if(et[gt].location>=0){let G=q[gt];G===void 0&&(gt==="instanceMatrix"&&L.instanceMatrix&&(G=L.instanceMatrix),gt==="instanceColor"&&L.instanceColor&&(G=L.instanceColor));const Q={};Q.attribute=G,G&&G.data&&(Q.data=G.data),X[gt]=Q,nt++}c.attributes=X,c.attributesNum=nt,c.index=J}function g(){const L=c.newAttributes;for(let k=0,z=L.length;k<z;k++)L[k]=0}function E(L){P(L,0)}function P(L,k){const z=c.newAttributes,J=c.enabledAttributes,X=c.attributeDivisors;z[L]=1,J[L]===0&&(i.enableVertexAttribArray(L),J[L]=1),X[L]!==k&&((n.isWebGL2?i:t.get("ANGLE_instanced_arrays"))[n.isWebGL2?"vertexAttribDivisor":"vertexAttribDivisorANGLE"](L,k),X[L]=k)}function w(){const L=c.newAttributes,k=c.enabledAttributes;for(let z=0,J=k.length;z<J;z++)k[z]!==L[z]&&(i.disableVertexAttribArray(z),k[z]=0)}function b(L,k,z,J,X,q,nt){nt===!0?i.vertexAttribIPointer(L,k,z,X,q):i.vertexAttribPointer(L,k,z,J,X,q)}function U(L,k,z,J){if(n.isWebGL2===!1&&(L.isInstancedMesh||J.isInstancedBufferGeometry)&&t.get("ANGLE_instanced_arrays")===null)return;g();const X=J.attributes,q=z.getAttributes(),nt=k.defaultAttributeValues;for(const et in q){const gt=q[et];if(gt.location>=0){let Pt=X[et];if(Pt===void 0&&(et==="instanceMatrix"&&L.instanceMatrix&&(Pt=L.instanceMatrix),et==="instanceColor"&&L.instanceColor&&(Pt=L.instanceColor)),Pt!==void 0){const G=Pt.normalized,Q=Pt.itemSize,pt=e.get(Pt);if(pt===void 0)continue;const Tt=pt.buffer,Mt=pt.type,vt=pt.bytesPerElement,Gt=n.isWebGL2===!0&&(Mt===i.INT||Mt===i.UNSIGNED_INT||Pt.gpuType===Do);if(Pt.isInterleavedBufferAttribute){const At=Pt.data,R=At.stride,at=Pt.offset;if(At.isInstancedInterleavedBuffer){for(let Y=0;Y<gt.locationSize;Y++)P(gt.location+Y,At.meshPerAttribute);L.isInstancedMesh!==!0&&J._maxInstanceCount===void 0&&(J._maxInstanceCount=At.meshPerAttribute*At.count)}else for(let Y=0;Y<gt.locationSize;Y++)E(gt.location+Y);i.bindBuffer(i.ARRAY_BUFFER,Tt);for(let Y=0;Y<gt.locationSize;Y++)b(gt.location+Y,Q/gt.locationSize,Mt,G,R*vt,(at+Q/gt.locationSize*Y)*vt,Gt)}else{if(Pt.isInstancedBufferAttribute){for(let At=0;At<gt.locationSize;At++)P(gt.location+At,Pt.meshPerAttribute);L.isInstancedMesh!==!0&&J._maxInstanceCount===void 0&&(J._maxInstanceCount=Pt.meshPerAttribute*Pt.count)}else for(let At=0;At<gt.locationSize;At++)E(gt.location+At);i.bindBuffer(i.ARRAY_BUFFER,Tt);for(let At=0;At<gt.locationSize;At++)b(gt.location+At,Q/gt.locationSize,Mt,G,Q*vt,Q/gt.locationSize*At*vt,Gt)}}else if(nt!==void 0){const G=nt[et];if(G!==void 0)switch(G.length){case 2:i.vertexAttrib2fv(gt.location,G);break;case 3:i.vertexAttrib3fv(gt.location,G);break;case 4:i.vertexAttrib4fv(gt.location,G);break;default:i.vertexAttrib1fv(gt.location,G)}}}}w()}function V(){Z();for(const L in a){const k=a[L];for(const z in k){const J=k[z];for(const X in J)_(J[X].object),delete J[X];delete k[z]}delete a[L]}}function v(L){if(a[L.id]===void 0)return;const k=a[L.id];for(const z in k){const J=k[z];for(const X in J)_(J[X].object),delete J[X];delete k[z]}delete a[L.id]}function A(L){for(const k in a){const z=a[k];if(z[L.id]===void 0)continue;const J=z[L.id];for(const X in J)_(J[X].object),delete J[X];delete z[L.id]}}function Z(){K(),h=!0,c!==l&&(c=l,m(c.object))}function K(){l.geometry=null,l.program=null,l.wireframe=!1}return{setup:u,reset:Z,resetDefaultState:K,dispose:V,releaseStatesOfGeometry:v,releaseStatesOfProgram:A,initAttributes:g,enableAttribute:E,disableUnusedAttributes:w}}function jf(i,t,e,n){const r=n.isWebGL2;let s;function o(h){s=h}function a(h,u){i.drawArrays(s,h,u),e.update(u,s,1)}function l(h,u,d){if(d===0)return;let m,_;if(r)m=i,_="drawArraysInstanced";else if(m=t.get("ANGLE_instanced_arrays"),_="drawArraysInstancedANGLE",m===null){console.error("THREE.WebGLBufferRenderer: using THREE.InstancedBufferGeometry but hardware does not support extension ANGLE_instanced_arrays.");return}m[_](s,h,u,d),e.update(u,s,d)}function c(h,u,d){if(d===0)return;const m=t.get("WEBGL_multi_draw");if(m===null)for(let _=0;_<d;_++)this.render(h[_],u[_]);else{m.multiDrawArraysWEBGL(s,h,0,u,0,d);let _=0;for(let M=0;M<d;M++)_+=u[M];e.update(_,s,1)}}this.setMode=o,this.render=a,this.renderInstances=l,this.renderMultiDraw=c}function Qf(i,t,e){let n;function r(){if(n!==void 0)return n;if(t.has("EXT_texture_filter_anisotropic")===!0){const b=t.get("EXT_texture_filter_anisotropic");n=i.getParameter(b.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else n=0;return n}function s(b){if(b==="highp"){if(i.getShaderPrecisionFormat(i.VERTEX_SHADER,i.HIGH_FLOAT).precision>0&&i.getShaderPrecisionFormat(i.FRAGMENT_SHADER,i.HIGH_FLOAT).precision>0)return"highp";b="mediump"}return b==="mediump"&&i.getShaderPrecisionFormat(i.VERTEX_SHADER,i.MEDIUM_FLOAT).precision>0&&i.getShaderPrecisionFormat(i.FRAGMENT_SHADER,i.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}const o=typeof WebGL2RenderingContext<"u"&&i.constructor.name==="WebGL2RenderingContext";let a=e.precision!==void 0?e.precision:"highp";const l=s(a);l!==a&&(console.warn("THREE.WebGLRenderer:",a,"not supported, using",l,"instead."),a=l);const c=o||t.has("WEBGL_draw_buffers"),h=e.logarithmicDepthBuffer===!0,u=i.getParameter(i.MAX_TEXTURE_IMAGE_UNITS),d=i.getParameter(i.MAX_VERTEX_TEXTURE_IMAGE_UNITS),m=i.getParameter(i.MAX_TEXTURE_SIZE),_=i.getParameter(i.MAX_CUBE_MAP_TEXTURE_SIZE),M=i.getParameter(i.MAX_VERTEX_ATTRIBS),p=i.getParameter(i.MAX_VERTEX_UNIFORM_VECTORS),f=i.getParameter(i.MAX_VARYING_VECTORS),y=i.getParameter(i.MAX_FRAGMENT_UNIFORM_VECTORS),g=d>0,E=o||t.has("OES_texture_float"),P=g&&E,w=o?i.getParameter(i.MAX_SAMPLES):0;return{isWebGL2:o,drawBuffers:c,getMaxAnisotropy:r,getMaxPrecision:s,precision:a,logarithmicDepthBuffer:h,maxTextures:u,maxVertexTextures:d,maxTextureSize:m,maxCubemapSize:_,maxAttributes:M,maxVertexUniforms:p,maxVaryings:f,maxFragmentUniforms:y,vertexTextures:g,floatFragmentTextures:E,floatVertexTextures:P,maxSamples:w}}function td(i){const t=this;let e=null,n=0,r=!1,s=!1;const o=new Tn,a=new Bt,l={value:null,needsUpdate:!1};this.uniform=l,this.numPlanes=0,this.numIntersection=0,this.init=function(u,d){const m=u.length!==0||d||n!==0||r;return r=d,n=u.length,m},this.beginShadows=function(){s=!0,h(null)},this.endShadows=function(){s=!1},this.setGlobalState=function(u,d){e=h(u,d,0)},this.setState=function(u,d,m){const _=u.clippingPlanes,M=u.clipIntersection,p=u.clipShadows,f=i.get(u);if(!r||_===null||_.length===0||s&&!p)s?h(null):c();else{const y=s?0:n,g=y*4;let E=f.clippingState||null;l.value=E,E=h(_,d,g,m);for(let P=0;P!==g;++P)E[P]=e[P];f.clippingState=E,this.numIntersection=M?this.numPlanes:0,this.numPlanes+=y}};function c(){l.value!==e&&(l.value=e,l.needsUpdate=n>0),t.numPlanes=n,t.numIntersection=0}function h(u,d,m,_){const M=u!==null?u.length:0;let p=null;if(M!==0){if(p=l.value,_!==!0||p===null){const f=m+M*4,y=d.matrixWorldInverse;a.getNormalMatrix(y),(p===null||p.length<f)&&(p=new Float32Array(f));for(let g=0,E=m;g!==M;++g,E+=4)o.copy(u[g]).applyMatrix4(y,a),o.normal.toArray(p,E),p[E+3]=o.constant}l.value=p,l.needsUpdate=!0}return t.numPlanes=M,t.numIntersection=0,p}}function ed(i){let t=new WeakMap;function e(o,a){return a===fs?o.mapping=ri:a===ds&&(o.mapping=si),o}function n(o){if(o&&o.isTexture){const a=o.mapping;if(a===fs||a===ds)if(t.has(o)){const l=t.get(o).texture;return e(l,o.mapping)}else{const l=o.image;if(l&&l.height>0){const c=new hh(l.height);return c.fromEquirectangularTexture(i,o),t.set(o,c),o.addEventListener("dispose",r),e(c.texture,o.mapping)}else return null}}return o}function r(o){const a=o.target;a.removeEventListener("dispose",r);const l=t.get(a);l!==void 0&&(t.delete(a),l.dispose())}function s(){t=new WeakMap}return{get:n,dispose:s}}class tl extends $o{constructor(t=-1,e=1,n=1,r=-1,s=.1,o=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=t,this.right=e,this.top=n,this.bottom=r,this.near=s,this.far=o,this.updateProjectionMatrix()}copy(t,e){return super.copy(t,e),this.left=t.left,this.right=t.right,this.top=t.top,this.bottom=t.bottom,this.near=t.near,this.far=t.far,this.zoom=t.zoom,this.view=t.view===null?null:Object.assign({},t.view),this}setViewOffset(t,e,n,r,s,o){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=t,this.view.fullHeight=e,this.view.offsetX=n,this.view.offsetY=r,this.view.width=s,this.view.height=o,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const t=(this.right-this.left)/(2*this.zoom),e=(this.top-this.bottom)/(2*this.zoom),n=(this.right+this.left)/2,r=(this.top+this.bottom)/2;let s=n-t,o=n+t,a=r+e,l=r-e;if(this.view!==null&&this.view.enabled){const c=(this.right-this.left)/this.view.fullWidth/this.zoom,h=(this.top-this.bottom)/this.view.fullHeight/this.zoom;s+=c*this.view.offsetX,o=s+c*this.view.width,a-=h*this.view.offsetY,l=a-h*this.view.height}this.projectionMatrix.makeOrthographic(s,o,a,l,this.near,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(t){const e=super.toJSON(t);return e.object.zoom=this.zoom,e.object.left=this.left,e.object.right=this.right,e.object.top=this.top,e.object.bottom=this.bottom,e.object.near=this.near,e.object.far=this.far,this.view!==null&&(e.object.view=Object.assign({},this.view)),e}}const Qn=4,Ha=[.125,.215,.35,.446,.526,.582],wn=20,jr=new tl,Va=new zt;let Qr=null,ts=0,es=0;const An=(1+Math.sqrt(5))/2,Kn=1/An,ka=[new C(1,1,1),new C(-1,1,1),new C(1,1,-1),new C(-1,1,-1),new C(0,An,Kn),new C(0,An,-Kn),new C(Kn,0,An),new C(-Kn,0,An),new C(An,Kn,0),new C(-An,Kn,0)];class Wa{constructor(t){this._renderer=t,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(t,e=0,n=.1,r=100){Qr=this._renderer.getRenderTarget(),ts=this._renderer.getActiveCubeFace(),es=this._renderer.getActiveMipmapLevel(),this._setSize(256);const s=this._allocateTargets();return s.depthBuffer=!0,this._sceneToCubeUV(t,n,r,s),e>0&&this._blur(s,0,0,e),this._applyPMREM(s),this._cleanup(s),s}fromEquirectangular(t,e=null){return this._fromTexture(t,e)}fromCubemap(t,e=null){return this._fromTexture(t,e)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=Ya(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=qa(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(t){this._lodMax=Math.floor(Math.log2(t)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let t=0;t<this._lodPlanes.length;t++)this._lodPlanes[t].dispose()}_cleanup(t){this._renderer.setRenderTarget(Qr,ts,es),t.scissorTest=!1,tr(t,0,0,t.width,t.height)}_fromTexture(t,e){t.mapping===ri||t.mapping===si?this._setSize(t.image.length===0?16:t.image[0].width||t.image[0].image.width):this._setSize(t.image.width/4),Qr=this._renderer.getRenderTarget(),ts=this._renderer.getActiveCubeFace(),es=this._renderer.getActiveMipmapLevel();const n=e||this._allocateTargets();return this._textureToCubeUV(t,n),this._applyPMREM(n),this._cleanup(n),n}_allocateTargets(){const t=3*Math.max(this._cubeSize,112),e=4*this._cubeSize,n={magFilter:ye,minFilter:ye,generateMipmaps:!1,type:Ai,format:Fe,colorSpace:mn,depthBuffer:!1},r=Xa(t,e,n);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==t||this._pingPongRenderTarget.height!==e){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=Xa(t,e,n);const{_lodMax:s}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=nd(s)),this._blurMaterial=id(s,t,e)}return r}_compileMaterial(t){const e=new Oe(this._lodPlanes[0],t);this._renderer.compile(e,jr)}_sceneToCubeUV(t,e,n,r){const a=new Pe(90,1,e,n),l=[1,-1,1,1,1,1],c=[1,1,1,-1,-1,-1],h=this._renderer,u=h.autoClear,d=h.toneMapping;h.getClearColor(Va),h.toneMapping=un,h.autoClear=!1;const m=new Yo({name:"PMREM.Background",side:Ee,depthWrite:!1,depthTest:!1}),_=new Oe(new Li,m);let M=!1;const p=t.background;p?p.isColor&&(m.color.copy(p),t.background=null,M=!0):(m.color.copy(Va),M=!0);for(let f=0;f<6;f++){const y=f%3;y===0?(a.up.set(0,l[f],0),a.lookAt(c[f],0,0)):y===1?(a.up.set(0,0,l[f]),a.lookAt(0,c[f],0)):(a.up.set(0,l[f],0),a.lookAt(0,0,c[f]));const g=this._cubeSize;tr(r,y*g,f>2?g:0,g,g),h.setRenderTarget(r),M&&h.render(_,a),h.render(t,a)}_.geometry.dispose(),_.material.dispose(),h.toneMapping=d,h.autoClear=u,t.background=p}_textureToCubeUV(t,e){const n=this._renderer,r=t.mapping===ri||t.mapping===si;r?(this._cubemapMaterial===null&&(this._cubemapMaterial=Ya()),this._cubemapMaterial.uniforms.flipEnvMap.value=t.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=qa());const s=r?this._cubemapMaterial:this._equirectMaterial,o=new Oe(this._lodPlanes[0],s),a=s.uniforms;a.envMap.value=t;const l=this._cubeSize;tr(e,0,0,3*l,2*l),n.setRenderTarget(e),n.render(o,jr)}_applyPMREM(t){const e=this._renderer,n=e.autoClear;e.autoClear=!1;for(let r=1;r<this._lodPlanes.length;r++){const s=Math.sqrt(this._sigmas[r]*this._sigmas[r]-this._sigmas[r-1]*this._sigmas[r-1]),o=ka[(r-1)%ka.length];this._blur(t,r-1,r,s,o)}e.autoClear=n}_blur(t,e,n,r,s){const o=this._pingPongRenderTarget;this._halfBlur(t,o,e,n,r,"latitudinal",s),this._halfBlur(o,t,n,n,r,"longitudinal",s)}_halfBlur(t,e,n,r,s,o,a){const l=this._renderer,c=this._blurMaterial;o!=="latitudinal"&&o!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");const h=3,u=new Oe(this._lodPlanes[r],c),d=c.uniforms,m=this._sizeLods[n]-1,_=isFinite(s)?Math.PI/(2*m):2*Math.PI/(2*wn-1),M=s/_,p=isFinite(s)?1+Math.floor(h*M):wn;p>wn&&console.warn(`sigmaRadians, ${s}, is too large and will clip, as it requested ${p} samples when the maximum is set to ${wn}`);const f=[];let y=0;for(let b=0;b<wn;++b){const U=b/M,V=Math.exp(-U*U/2);f.push(V),b===0?y+=V:b<p&&(y+=2*V)}for(let b=0;b<f.length;b++)f[b]=f[b]/y;d.envMap.value=t.texture,d.samples.value=p,d.weights.value=f,d.latitudinal.value=o==="latitudinal",a&&(d.poleAxis.value=a);const{_lodMax:g}=this;d.dTheta.value=_,d.mipInt.value=g-n;const E=this._sizeLods[r],P=3*E*(r>g-Qn?r-g+Qn:0),w=4*(this._cubeSize-E);tr(e,P,w,3*E,2*E),l.setRenderTarget(e),l.render(u,jr)}}function nd(i){const t=[],e=[],n=[];let r=i;const s=i-Qn+1+Ha.length;for(let o=0;o<s;o++){const a=Math.pow(2,r);e.push(a);let l=1/a;o>i-Qn?l=Ha[o-i+Qn-1]:o===0&&(l=0),n.push(l);const c=1/(a-2),h=-c,u=1+c,d=[h,h,u,h,u,u,h,h,u,u,h,u],m=6,_=6,M=3,p=2,f=1,y=new Float32Array(M*_*m),g=new Float32Array(p*_*m),E=new Float32Array(f*_*m);for(let w=0;w<m;w++){const b=w%3*2/3-1,U=w>2?0:-1,V=[b,U,0,b+2/3,U,0,b+2/3,U+1,0,b,U,0,b+2/3,U+1,0,b,U+1,0];y.set(V,M*_*w),g.set(d,p*_*w);const v=[w,w,w,w,w,w];E.set(v,f*_*w)}const P=new pe;P.setAttribute("position",new Le(y,M)),P.setAttribute("uv",new Le(g,p)),P.setAttribute("faceIndex",new Le(E,f)),t.push(P),r>Qn&&r--}return{lodPlanes:t,sizeLods:e,sigmas:n}}function Xa(i,t,e){const n=new Ln(i,t,e);return n.texture.mapping=mr,n.texture.name="PMREM.cubeUv",n.scissorTest=!0,n}function tr(i,t,e,n,r){i.viewport.set(t,e,n,r),i.scissor.set(t,e,n,r)}function id(i,t,e){const n=new Float32Array(wn),r=new C(0,1,0);return new tn({name:"SphericalGaussianBlur",defines:{n:wn,CUBEUV_TEXEL_WIDTH:1/t,CUBEUV_TEXEL_HEIGHT:1/e,CUBEUV_MAX_MIP:`${i}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:n},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:r}},vertexShader:Ps(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,blending:hn,depthTest:!1,depthWrite:!1})}function qa(){return new tn({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:Ps(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:hn,depthTest:!1,depthWrite:!1})}function Ya(){return new tn({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:Ps(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:hn,depthTest:!1,depthWrite:!1})}function Ps(){return`

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`}function rd(i){let t=new WeakMap,e=null;function n(a){if(a&&a.isTexture){const l=a.mapping,c=l===fs||l===ds,h=l===ri||l===si;if(c||h)if(a.isRenderTargetTexture&&a.needsPMREMUpdate===!0){a.needsPMREMUpdate=!1;let u=t.get(a);return e===null&&(e=new Wa(i)),u=c?e.fromEquirectangular(a,u):e.fromCubemap(a,u),t.set(a,u),u.texture}else{if(t.has(a))return t.get(a).texture;{const u=a.image;if(c&&u&&u.height>0||h&&u&&r(u)){e===null&&(e=new Wa(i));const d=c?e.fromEquirectangular(a):e.fromCubemap(a);return t.set(a,d),a.addEventListener("dispose",s),d.texture}else return null}}}return a}function r(a){let l=0;const c=6;for(let h=0;h<c;h++)a[h]!==void 0&&l++;return l===c}function s(a){const l=a.target;l.removeEventListener("dispose",s);const c=t.get(l);c!==void 0&&(t.delete(l),c.dispose())}function o(){t=new WeakMap,e!==null&&(e.dispose(),e=null)}return{get:n,dispose:o}}function sd(i){const t={};function e(n){if(t[n]!==void 0)return t[n];let r;switch(n){case"WEBGL_depth_texture":r=i.getExtension("WEBGL_depth_texture")||i.getExtension("MOZ_WEBGL_depth_texture")||i.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":r=i.getExtension("EXT_texture_filter_anisotropic")||i.getExtension("MOZ_EXT_texture_filter_anisotropic")||i.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":r=i.getExtension("WEBGL_compressed_texture_s3tc")||i.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||i.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":r=i.getExtension("WEBGL_compressed_texture_pvrtc")||i.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:r=i.getExtension(n)}return t[n]=r,r}return{has:function(n){return e(n)!==null},init:function(n){n.isWebGL2?(e("EXT_color_buffer_float"),e("WEBGL_clip_cull_distance")):(e("WEBGL_depth_texture"),e("OES_texture_float"),e("OES_texture_half_float"),e("OES_texture_half_float_linear"),e("OES_standard_derivatives"),e("OES_element_index_uint"),e("OES_vertex_array_object"),e("ANGLE_instanced_arrays")),e("OES_texture_float_linear"),e("EXT_color_buffer_half_float"),e("WEBGL_multisampled_render_to_texture")},get:function(n){const r=e(n);return r===null&&console.warn("THREE.WebGLRenderer: "+n+" extension not supported."),r}}}function ad(i,t,e,n){const r={},s=new WeakMap;function o(u){const d=u.target;d.index!==null&&t.remove(d.index);for(const _ in d.attributes)t.remove(d.attributes[_]);for(const _ in d.morphAttributes){const M=d.morphAttributes[_];for(let p=0,f=M.length;p<f;p++)t.remove(M[p])}d.removeEventListener("dispose",o),delete r[d.id];const m=s.get(d);m&&(t.remove(m),s.delete(d)),n.releaseStatesOfGeometry(d),d.isInstancedBufferGeometry===!0&&delete d._maxInstanceCount,e.memory.geometries--}function a(u,d){return r[d.id]===!0||(d.addEventListener("dispose",o),r[d.id]=!0,e.memory.geometries++),d}function l(u){const d=u.attributes;for(const _ in d)t.update(d[_],i.ARRAY_BUFFER);const m=u.morphAttributes;for(const _ in m){const M=m[_];for(let p=0,f=M.length;p<f;p++)t.update(M[p],i.ARRAY_BUFFER)}}function c(u){const d=[],m=u.index,_=u.attributes.position;let M=0;if(m!==null){const y=m.array;M=m.version;for(let g=0,E=y.length;g<E;g+=3){const P=y[g+0],w=y[g+1],b=y[g+2];d.push(P,w,w,b,b,P)}}else if(_!==void 0){const y=_.array;M=_.version;for(let g=0,E=y.length/3-1;g<E;g+=3){const P=g+0,w=g+1,b=g+2;d.push(P,w,w,b,b,P)}}else return;const p=new(Vo(d)?Zo:Jo)(d,1);p.version=M;const f=s.get(u);f&&t.remove(f),s.set(u,p)}function h(u){const d=s.get(u);if(d){const m=u.index;m!==null&&d.version<m.version&&c(u)}else c(u);return s.get(u)}return{get:a,update:l,getWireframeAttribute:h}}function od(i,t,e,n){const r=n.isWebGL2;let s;function o(m){s=m}let a,l;function c(m){a=m.type,l=m.bytesPerElement}function h(m,_){i.drawElements(s,_,a,m*l),e.update(_,s,1)}function u(m,_,M){if(M===0)return;let p,f;if(r)p=i,f="drawElementsInstanced";else if(p=t.get("ANGLE_instanced_arrays"),f="drawElementsInstancedANGLE",p===null){console.error("THREE.WebGLIndexedBufferRenderer: using THREE.InstancedBufferGeometry but hardware does not support extension ANGLE_instanced_arrays.");return}p[f](s,_,a,m*l,M),e.update(_,s,M)}function d(m,_,M){if(M===0)return;const p=t.get("WEBGL_multi_draw");if(p===null)for(let f=0;f<M;f++)this.render(m[f]/l,_[f]);else{p.multiDrawElementsWEBGL(s,_,0,a,m,0,M);let f=0;for(let y=0;y<M;y++)f+=_[y];e.update(f,s,1)}}this.setMode=o,this.setIndex=c,this.render=h,this.renderInstances=u,this.renderMultiDraw=d}function ld(i){const t={geometries:0,textures:0},e={frame:0,calls:0,triangles:0,points:0,lines:0};function n(s,o,a){switch(e.calls++,o){case i.TRIANGLES:e.triangles+=a*(s/3);break;case i.LINES:e.lines+=a*(s/2);break;case i.LINE_STRIP:e.lines+=a*(s-1);break;case i.LINE_LOOP:e.lines+=a*s;break;case i.POINTS:e.points+=a*s;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",o);break}}function r(){e.calls=0,e.triangles=0,e.points=0,e.lines=0}return{memory:t,render:e,programs:null,autoReset:!0,reset:r,update:n}}function cd(i,t){return i[0]-t[0]}function hd(i,t){return Math.abs(t[1])-Math.abs(i[1])}function ud(i,t,e){const n={},r=new Float32Array(8),s=new WeakMap,o=new te,a=[];for(let c=0;c<8;c++)a[c]=[c,0];function l(c,h,u){const d=c.morphTargetInfluences;if(t.isWebGL2===!0){const m=h.morphAttributes.position||h.morphAttributes.normal||h.morphAttributes.color,_=m!==void 0?m.length:0;let M=s.get(h);if(M===void 0||M.count!==_){let Z=function(){v.dispose(),s.delete(h),h.removeEventListener("dispose",Z)};M!==void 0&&M.texture.dispose();const p=h.morphAttributes.position!==void 0,f=h.morphAttributes.normal!==void 0,y=h.morphAttributes.color!==void 0,g=h.morphAttributes.position||[],E=h.morphAttributes.normal||[],P=h.morphAttributes.color||[];let w=0;p===!0&&(w=1),f===!0&&(w=2),y===!0&&(w=3);let b=h.attributes.position.count*w,U=1;b>t.maxTextureSize&&(U=Math.ceil(b/t.maxTextureSize),b=t.maxTextureSize);const V=new Float32Array(b*U*4*_),v=new Xo(V,b,U,_);v.type=He,v.needsUpdate=!0;const A=w*4;for(let K=0;K<_;K++){const L=g[K],k=E[K],z=P[K],J=b*U*4*K;for(let X=0;X<L.count;X++){const q=X*A;p===!0&&(o.fromBufferAttribute(L,X),V[J+q+0]=o.x,V[J+q+1]=o.y,V[J+q+2]=o.z,V[J+q+3]=0),f===!0&&(o.fromBufferAttribute(k,X),V[J+q+4]=o.x,V[J+q+5]=o.y,V[J+q+6]=o.z,V[J+q+7]=0),y===!0&&(o.fromBufferAttribute(z,X),V[J+q+8]=o.x,V[J+q+9]=o.y,V[J+q+10]=o.z,V[J+q+11]=z.itemSize===4?o.w:1)}}M={count:_,texture:v,size:new it(b,U)},s.set(h,M),h.addEventListener("dispose",Z)}if(c.isInstancedMesh===!0&&c.morphTexture!==null)u.getUniforms().setValue(i,"morphTexture",c.morphTexture,e);else{let p=0;for(let y=0;y<d.length;y++)p+=d[y];const f=h.morphTargetsRelative?1:1-p;u.getUniforms().setValue(i,"morphTargetBaseInfluence",f),u.getUniforms().setValue(i,"morphTargetInfluences",d)}u.getUniforms().setValue(i,"morphTargetsTexture",M.texture,e),u.getUniforms().setValue(i,"morphTargetsTextureSize",M.size)}else{const m=d===void 0?0:d.length;let _=n[h.id];if(_===void 0||_.length!==m){_=[];for(let g=0;g<m;g++)_[g]=[g,0];n[h.id]=_}for(let g=0;g<m;g++){const E=_[g];E[0]=g,E[1]=d[g]}_.sort(hd);for(let g=0;g<8;g++)g<m&&_[g][1]?(a[g][0]=_[g][0],a[g][1]=_[g][1]):(a[g][0]=Number.MAX_SAFE_INTEGER,a[g][1]=0);a.sort(cd);const M=h.morphAttributes.position,p=h.morphAttributes.normal;let f=0;for(let g=0;g<8;g++){const E=a[g],P=E[0],w=E[1];P!==Number.MAX_SAFE_INTEGER&&w?(M&&h.getAttribute("morphTarget"+g)!==M[P]&&h.setAttribute("morphTarget"+g,M[P]),p&&h.getAttribute("morphNormal"+g)!==p[P]&&h.setAttribute("morphNormal"+g,p[P]),r[g]=w,f+=w):(M&&h.hasAttribute("morphTarget"+g)===!0&&h.deleteAttribute("morphTarget"+g),p&&h.hasAttribute("morphNormal"+g)===!0&&h.deleteAttribute("morphNormal"+g),r[g]=0)}const y=h.morphTargetsRelative?1:1-f;u.getUniforms().setValue(i,"morphTargetBaseInfluence",y),u.getUniforms().setValue(i,"morphTargetInfluences",r)}}return{update:l}}function fd(i,t,e,n){let r=new WeakMap;function s(l){const c=n.render.frame,h=l.geometry,u=t.get(l,h);if(r.get(u)!==c&&(t.update(u),r.set(u,c)),l.isInstancedMesh&&(l.hasEventListener("dispose",a)===!1&&l.addEventListener("dispose",a),r.get(l)!==c&&(e.update(l.instanceMatrix,i.ARRAY_BUFFER),l.instanceColor!==null&&e.update(l.instanceColor,i.ARRAY_BUFFER),r.set(l,c))),l.isSkinnedMesh){const d=l.skeleton;r.get(d)!==c&&(d.update(),r.set(d,c))}return u}function o(){r=new WeakMap}function a(l){const c=l.target;c.removeEventListener("dispose",a),e.remove(c.instanceMatrix),c.instanceColor!==null&&e.remove(c.instanceColor)}return{update:s,dispose:o}}class el extends ve{constructor(t,e,n,r,s,o,a,l,c,h){if(h=h!==void 0?h:Pn,h!==Pn&&h!==ai)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");n===void 0&&h===Pn&&(n=cn),n===void 0&&h===ai&&(n=Cn),super(null,r,s,o,a,l,h,n,c),this.isDepthTexture=!0,this.image={width:t,height:e},this.magFilter=a!==void 0?a:de,this.minFilter=l!==void 0?l:de,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(t){return super.copy(t),this.compareFunction=t.compareFunction,this}toJSON(t){const e=super.toJSON(t);return this.compareFunction!==null&&(e.compareFunction=this.compareFunction),e}}const nl=new ve,il=new el(1,1);il.compareFunction=Ho;const rl=new Xo,sl=new Yc,al=new jo,Ja=[],Za=[],Ka=new Float32Array(16),$a=new Float32Array(9),ja=new Float32Array(4);function ui(i,t,e){const n=i[0];if(n<=0||n>0)return i;const r=t*e;let s=Ja[r];if(s===void 0&&(s=new Float32Array(r),Ja[r]=s),t!==0){n.toArray(s,0);for(let o=1,a=0;o!==t;++o)a+=e,i[o].toArray(s,a)}return s}function oe(i,t){if(i.length!==t.length)return!1;for(let e=0,n=i.length;e<n;e++)if(i[e]!==t[e])return!1;return!0}function le(i,t){for(let e=0,n=t.length;e<n;e++)i[e]=t[e]}function vr(i,t){let e=Za[t];e===void 0&&(e=new Int32Array(t),Za[t]=e);for(let n=0;n!==t;++n)e[n]=i.allocateTextureUnit();return e}function dd(i,t){const e=this.cache;e[0]!==t&&(i.uniform1f(this.addr,t),e[0]=t)}function pd(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2f(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(oe(e,t))return;i.uniform2fv(this.addr,t),le(e,t)}}function md(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3f(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else if(t.r!==void 0)(e[0]!==t.r||e[1]!==t.g||e[2]!==t.b)&&(i.uniform3f(this.addr,t.r,t.g,t.b),e[0]=t.r,e[1]=t.g,e[2]=t.b);else{if(oe(e,t))return;i.uniform3fv(this.addr,t),le(e,t)}}function gd(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4f(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(oe(e,t))return;i.uniform4fv(this.addr,t),le(e,t)}}function _d(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(oe(e,t))return;i.uniformMatrix2fv(this.addr,!1,t),le(e,t)}else{if(oe(e,n))return;ja.set(n),i.uniformMatrix2fv(this.addr,!1,ja),le(e,n)}}function vd(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(oe(e,t))return;i.uniformMatrix3fv(this.addr,!1,t),le(e,t)}else{if(oe(e,n))return;$a.set(n),i.uniformMatrix3fv(this.addr,!1,$a),le(e,n)}}function xd(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(oe(e,t))return;i.uniformMatrix4fv(this.addr,!1,t),le(e,t)}else{if(oe(e,n))return;Ka.set(n),i.uniformMatrix4fv(this.addr,!1,Ka),le(e,n)}}function Md(i,t){const e=this.cache;e[0]!==t&&(i.uniform1i(this.addr,t),e[0]=t)}function Sd(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2i(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(oe(e,t))return;i.uniform2iv(this.addr,t),le(e,t)}}function yd(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3i(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else{if(oe(e,t))return;i.uniform3iv(this.addr,t),le(e,t)}}function Ed(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4i(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(oe(e,t))return;i.uniform4iv(this.addr,t),le(e,t)}}function Td(i,t){const e=this.cache;e[0]!==t&&(i.uniform1ui(this.addr,t),e[0]=t)}function Ad(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2ui(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(oe(e,t))return;i.uniform2uiv(this.addr,t),le(e,t)}}function bd(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3ui(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else{if(oe(e,t))return;i.uniform3uiv(this.addr,t),le(e,t)}}function wd(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4ui(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(oe(e,t))return;i.uniform4uiv(this.addr,t),le(e,t)}}function Rd(i,t,e){const n=this.cache,r=e.allocateTextureUnit();n[0]!==r&&(i.uniform1i(this.addr,r),n[0]=r);const s=this.type===i.SAMPLER_2D_SHADOW?il:nl;e.setTexture2D(t||s,r)}function Cd(i,t,e){const n=this.cache,r=e.allocateTextureUnit();n[0]!==r&&(i.uniform1i(this.addr,r),n[0]=r),e.setTexture3D(t||sl,r)}function Pd(i,t,e){const n=this.cache,r=e.allocateTextureUnit();n[0]!==r&&(i.uniform1i(this.addr,r),n[0]=r),e.setTextureCube(t||al,r)}function Ld(i,t,e){const n=this.cache,r=e.allocateTextureUnit();n[0]!==r&&(i.uniform1i(this.addr,r),n[0]=r),e.setTexture2DArray(t||rl,r)}function Dd(i){switch(i){case 5126:return dd;case 35664:return pd;case 35665:return md;case 35666:return gd;case 35674:return _d;case 35675:return vd;case 35676:return xd;case 5124:case 35670:return Md;case 35667:case 35671:return Sd;case 35668:case 35672:return yd;case 35669:case 35673:return Ed;case 5125:return Td;case 36294:return Ad;case 36295:return bd;case 36296:return wd;case 35678:case 36198:case 36298:case 36306:case 35682:return Rd;case 35679:case 36299:case 36307:return Cd;case 35680:case 36300:case 36308:case 36293:return Pd;case 36289:case 36303:case 36311:case 36292:return Ld}}function Ud(i,t){i.uniform1fv(this.addr,t)}function Id(i,t){const e=ui(t,this.size,2);i.uniform2fv(this.addr,e)}function Nd(i,t){const e=ui(t,this.size,3);i.uniform3fv(this.addr,e)}function Fd(i,t){const e=ui(t,this.size,4);i.uniform4fv(this.addr,e)}function Od(i,t){const e=ui(t,this.size,4);i.uniformMatrix2fv(this.addr,!1,e)}function Bd(i,t){const e=ui(t,this.size,9);i.uniformMatrix3fv(this.addr,!1,e)}function zd(i,t){const e=ui(t,this.size,16);i.uniformMatrix4fv(this.addr,!1,e)}function Gd(i,t){i.uniform1iv(this.addr,t)}function Hd(i,t){i.uniform2iv(this.addr,t)}function Vd(i,t){i.uniform3iv(this.addr,t)}function kd(i,t){i.uniform4iv(this.addr,t)}function Wd(i,t){i.uniform1uiv(this.addr,t)}function Xd(i,t){i.uniform2uiv(this.addr,t)}function qd(i,t){i.uniform3uiv(this.addr,t)}function Yd(i,t){i.uniform4uiv(this.addr,t)}function Jd(i,t,e){const n=this.cache,r=t.length,s=vr(e,r);oe(n,s)||(i.uniform1iv(this.addr,s),le(n,s));for(let o=0;o!==r;++o)e.setTexture2D(t[o]||nl,s[o])}function Zd(i,t,e){const n=this.cache,r=t.length,s=vr(e,r);oe(n,s)||(i.uniform1iv(this.addr,s),le(n,s));for(let o=0;o!==r;++o)e.setTexture3D(t[o]||sl,s[o])}function Kd(i,t,e){const n=this.cache,r=t.length,s=vr(e,r);oe(n,s)||(i.uniform1iv(this.addr,s),le(n,s));for(let o=0;o!==r;++o)e.setTextureCube(t[o]||al,s[o])}function $d(i,t,e){const n=this.cache,r=t.length,s=vr(e,r);oe(n,s)||(i.uniform1iv(this.addr,s),le(n,s));for(let o=0;o!==r;++o)e.setTexture2DArray(t[o]||rl,s[o])}function jd(i){switch(i){case 5126:return Ud;case 35664:return Id;case 35665:return Nd;case 35666:return Fd;case 35674:return Od;case 35675:return Bd;case 35676:return zd;case 5124:case 35670:return Gd;case 35667:case 35671:return Hd;case 35668:case 35672:return Vd;case 35669:case 35673:return kd;case 5125:return Wd;case 36294:return Xd;case 36295:return qd;case 36296:return Yd;case 35678:case 36198:case 36298:case 36306:case 35682:return Jd;case 35679:case 36299:case 36307:return Zd;case 35680:case 36300:case 36308:case 36293:return Kd;case 36289:case 36303:case 36311:case 36292:return $d}}class Qd{constructor(t,e,n){this.id=t,this.addr=n,this.cache=[],this.type=e.type,this.setValue=Dd(e.type)}}class tp{constructor(t,e,n){this.id=t,this.addr=n,this.cache=[],this.type=e.type,this.size=e.size,this.setValue=jd(e.type)}}class ep{constructor(t){this.id=t,this.seq=[],this.map={}}setValue(t,e,n){const r=this.seq;for(let s=0,o=r.length;s!==o;++s){const a=r[s];a.setValue(t,e[a.id],n)}}}const ns=/(\w+)(\])?(\[|\.)?/g;function Qa(i,t){i.seq.push(t),i.map[t.id]=t}function np(i,t,e){const n=i.name,r=n.length;for(ns.lastIndex=0;;){const s=ns.exec(n),o=ns.lastIndex;let a=s[1];const l=s[2]==="]",c=s[3];if(l&&(a=a|0),c===void 0||c==="["&&o+2===r){Qa(e,c===void 0?new Qd(a,i,t):new tp(a,i,t));break}else{let u=e.map[a];u===void 0&&(u=new ep(a),Qa(e,u)),e=u}}}class or{constructor(t,e){this.seq=[],this.map={};const n=t.getProgramParameter(e,t.ACTIVE_UNIFORMS);for(let r=0;r<n;++r){const s=t.getActiveUniform(e,r),o=t.getUniformLocation(e,s.name);np(s,o,this)}}setValue(t,e,n,r){const s=this.map[e];s!==void 0&&s.setValue(t,n,r)}setOptional(t,e,n){const r=e[n];r!==void 0&&this.setValue(t,n,r)}static upload(t,e,n,r){for(let s=0,o=e.length;s!==o;++s){const a=e[s],l=n[a.id];l.needsUpdate!==!1&&a.setValue(t,l.value,r)}}static seqWithValue(t,e){const n=[];for(let r=0,s=t.length;r!==s;++r){const o=t[r];o.id in e&&n.push(o)}return n}}function to(i,t,e){const n=i.createShader(t);return i.shaderSource(n,e),i.compileShader(n),n}const ip=37297;let rp=0;function sp(i,t){const e=i.split(`
`),n=[],r=Math.max(t-6,0),s=Math.min(t+6,e.length);for(let o=r;o<s;o++){const a=o+1;n.push(`${a===t?">":" "} ${a}: ${e[o]}`)}return n.join(`
`)}function ap(i){const t=Yt.getPrimaries(Yt.workingColorSpace),e=Yt.getPrimaries(i);let n;switch(t===e?n="":t===ur&&e===hr?n="LinearDisplayP3ToLinearSRGB":t===hr&&e===ur&&(n="LinearSRGBToLinearDisplayP3"),i){case mn:case gr:return[n,"LinearTransferOETF"];case ze:case As:return[n,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space:",i),[n,"LinearTransferOETF"]}}function eo(i,t,e){const n=i.getShaderParameter(t,i.COMPILE_STATUS),r=i.getShaderInfoLog(t).trim();if(n&&r==="")return"";const s=/ERROR: 0:(\d+)/.exec(r);if(s){const o=parseInt(s[1]);return e.toUpperCase()+`

`+r+`

`+sp(i.getShaderSource(t),o)}else return r}function op(i,t){const e=ap(t);return`vec4 ${i}( vec4 value ) { return ${e[0]}( ${e[1]}( value ) ); }`}function lp(i,t){let e;switch(t){case ic:e="Linear";break;case rc:e="Reinhard";break;case sc:e="OptimizedCineon";break;case ac:e="ACESFilmic";break;case lc:e="AgX";break;case cc:e="Neutral";break;case oc:e="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",t),e="Linear"}return"vec3 "+i+"( vec3 color ) { return "+e+"ToneMapping( color ); }"}function cp(i){return[i.extensionDerivatives||i.envMapCubeUVHeight||i.bumpMap||i.normalMapTangentSpace||i.clearcoatNormalMap||i.flatShading||i.alphaToCoverage||i.shaderID==="physical"?"#extension GL_OES_standard_derivatives : enable":"",(i.extensionFragDepth||i.logarithmicDepthBuffer)&&i.rendererExtensionFragDepth?"#extension GL_EXT_frag_depth : enable":"",i.extensionDrawBuffers&&i.rendererExtensionDrawBuffers?"#extension GL_EXT_draw_buffers : require":"",(i.extensionShaderTextureLOD||i.envMap||i.transmission)&&i.rendererExtensionShaderTextureLod?"#extension GL_EXT_shader_texture_lod : enable":""].filter(ti).join(`
`)}function hp(i){return[i.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",i.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(ti).join(`
`)}function up(i){const t=[];for(const e in i){const n=i[e];n!==!1&&t.push("#define "+e+" "+n)}return t.join(`
`)}function fp(i,t){const e={},n=i.getProgramParameter(t,i.ACTIVE_ATTRIBUTES);for(let r=0;r<n;r++){const s=i.getActiveAttrib(t,r),o=s.name;let a=1;s.type===i.FLOAT_MAT2&&(a=2),s.type===i.FLOAT_MAT3&&(a=3),s.type===i.FLOAT_MAT4&&(a=4),e[o]={type:s.type,location:i.getAttribLocation(t,o),locationSize:a}}return e}function ti(i){return i!==""}function no(i,t){const e=t.numSpotLightShadows+t.numSpotLightMaps-t.numSpotLightShadowsWithMaps;return i.replace(/NUM_DIR_LIGHTS/g,t.numDirLights).replace(/NUM_SPOT_LIGHTS/g,t.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,t.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,e).replace(/NUM_RECT_AREA_LIGHTS/g,t.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,t.numPointLights).replace(/NUM_HEMI_LIGHTS/g,t.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,t.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,t.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,t.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,t.numPointLightShadows)}function io(i,t){return i.replace(/NUM_CLIPPING_PLANES/g,t.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,t.numClippingPlanes-t.numClipIntersection)}const dp=/^[ \t]*#include +<([\w\d./]+)>/gm;function vs(i){return i.replace(dp,mp)}const pp=new Map([["encodings_fragment","colorspace_fragment"],["encodings_pars_fragment","colorspace_pars_fragment"],["output_fragment","opaque_fragment"]]);function mp(i,t){let e=Ot[t];if(e===void 0){const n=pp.get(t);if(n!==void 0)e=Ot[n],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',t,n);else throw new Error("Can not resolve #include <"+t+">")}return vs(e)}const gp=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function ro(i){return i.replace(gp,_p)}function _p(i,t,e,n){let r="";for(let s=parseInt(t);s<parseInt(e);s++)r+=n.replace(/\[\s*i\s*\]/g,"[ "+s+" ]").replace(/UNROLLED_LOOP_INDEX/g,s);return r}function so(i){let t=`precision ${i.precision} float;
	precision ${i.precision} int;
	precision ${i.precision} sampler2D;
	precision ${i.precision} samplerCube;
	`;return i.isWebGL2&&(t+=`precision ${i.precision} sampler3D;
		precision ${i.precision} sampler2DArray;
		precision ${i.precision} sampler2DShadow;
		precision ${i.precision} samplerCubeShadow;
		precision ${i.precision} sampler2DArrayShadow;
		precision ${i.precision} isampler2D;
		precision ${i.precision} isampler3D;
		precision ${i.precision} isamplerCube;
		precision ${i.precision} isampler2DArray;
		precision ${i.precision} usampler2D;
		precision ${i.precision} usampler3D;
		precision ${i.precision} usamplerCube;
		precision ${i.precision} usampler2DArray;
		`),i.precision==="highp"?t+=`
#define HIGH_PRECISION`:i.precision==="mediump"?t+=`
#define MEDIUM_PRECISION`:i.precision==="lowp"&&(t+=`
#define LOW_PRECISION`),t}function vp(i){let t="SHADOWMAP_TYPE_BASIC";return i.shadowMapType===Co?t="SHADOWMAP_TYPE_PCF":i.shadowMapType===Ll?t="SHADOWMAP_TYPE_PCF_SOFT":i.shadowMapType===$e&&(t="SHADOWMAP_TYPE_VSM"),t}function xp(i){let t="ENVMAP_TYPE_CUBE";if(i.envMap)switch(i.envMapMode){case ri:case si:t="ENVMAP_TYPE_CUBE";break;case mr:t="ENVMAP_TYPE_CUBE_UV";break}return t}function Mp(i){let t="ENVMAP_MODE_REFLECTION";if(i.envMap)switch(i.envMapMode){case si:t="ENVMAP_MODE_REFRACTION";break}return t}function Sp(i){let t="ENVMAP_BLENDING_NONE";if(i.envMap)switch(i.combine){case Po:t="ENVMAP_BLENDING_MULTIPLY";break;case ec:t="ENVMAP_BLENDING_MIX";break;case nc:t="ENVMAP_BLENDING_ADD";break}return t}function yp(i){const t=i.envMapCubeUVHeight;if(t===null)return null;const e=Math.log2(t)-2,n=1/t;return{texelWidth:1/(3*Math.max(Math.pow(2,e),7*16)),texelHeight:n,maxMip:e}}function Ep(i,t,e,n){const r=i.getContext(),s=e.defines;let o=e.vertexShader,a=e.fragmentShader;const l=vp(e),c=xp(e),h=Mp(e),u=Sp(e),d=yp(e),m=e.isWebGL2?"":cp(e),_=hp(e),M=up(s),p=r.createProgram();let f,y,g=e.glslVersion?"#version "+e.glslVersion+`
`:"";e.isRawShaderMaterial?(f=["#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,M].filter(ti).join(`
`),f.length>0&&(f+=`
`),y=[m,"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,M].filter(ti).join(`
`),y.length>0&&(y+=`
`)):(f=[so(e),"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,M,e.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",e.batching?"#define USE_BATCHING":"",e.instancing?"#define USE_INSTANCING":"",e.instancingColor?"#define USE_INSTANCING_COLOR":"",e.instancingMorph?"#define USE_INSTANCING_MORPH":"",e.useFog&&e.fog?"#define USE_FOG":"",e.useFog&&e.fogExp2?"#define FOG_EXP2":"",e.map?"#define USE_MAP":"",e.envMap?"#define USE_ENVMAP":"",e.envMap?"#define "+h:"",e.lightMap?"#define USE_LIGHTMAP":"",e.aoMap?"#define USE_AOMAP":"",e.bumpMap?"#define USE_BUMPMAP":"",e.normalMap?"#define USE_NORMALMAP":"",e.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",e.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",e.displacementMap?"#define USE_DISPLACEMENTMAP":"",e.emissiveMap?"#define USE_EMISSIVEMAP":"",e.anisotropy?"#define USE_ANISOTROPY":"",e.anisotropyMap?"#define USE_ANISOTROPYMAP":"",e.clearcoatMap?"#define USE_CLEARCOATMAP":"",e.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",e.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",e.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",e.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",e.specularMap?"#define USE_SPECULARMAP":"",e.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",e.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",e.roughnessMap?"#define USE_ROUGHNESSMAP":"",e.metalnessMap?"#define USE_METALNESSMAP":"",e.alphaMap?"#define USE_ALPHAMAP":"",e.alphaHash?"#define USE_ALPHAHASH":"",e.transmission?"#define USE_TRANSMISSION":"",e.transmissionMap?"#define USE_TRANSMISSIONMAP":"",e.thicknessMap?"#define USE_THICKNESSMAP":"",e.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",e.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",e.mapUv?"#define MAP_UV "+e.mapUv:"",e.alphaMapUv?"#define ALPHAMAP_UV "+e.alphaMapUv:"",e.lightMapUv?"#define LIGHTMAP_UV "+e.lightMapUv:"",e.aoMapUv?"#define AOMAP_UV "+e.aoMapUv:"",e.emissiveMapUv?"#define EMISSIVEMAP_UV "+e.emissiveMapUv:"",e.bumpMapUv?"#define BUMPMAP_UV "+e.bumpMapUv:"",e.normalMapUv?"#define NORMALMAP_UV "+e.normalMapUv:"",e.displacementMapUv?"#define DISPLACEMENTMAP_UV "+e.displacementMapUv:"",e.metalnessMapUv?"#define METALNESSMAP_UV "+e.metalnessMapUv:"",e.roughnessMapUv?"#define ROUGHNESSMAP_UV "+e.roughnessMapUv:"",e.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+e.anisotropyMapUv:"",e.clearcoatMapUv?"#define CLEARCOATMAP_UV "+e.clearcoatMapUv:"",e.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+e.clearcoatNormalMapUv:"",e.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+e.clearcoatRoughnessMapUv:"",e.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+e.iridescenceMapUv:"",e.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+e.iridescenceThicknessMapUv:"",e.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+e.sheenColorMapUv:"",e.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+e.sheenRoughnessMapUv:"",e.specularMapUv?"#define SPECULARMAP_UV "+e.specularMapUv:"",e.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+e.specularColorMapUv:"",e.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+e.specularIntensityMapUv:"",e.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+e.transmissionMapUv:"",e.thicknessMapUv?"#define THICKNESSMAP_UV "+e.thicknessMapUv:"",e.vertexTangents&&e.flatShading===!1?"#define USE_TANGENT":"",e.vertexColors?"#define USE_COLOR":"",e.vertexAlphas?"#define USE_COLOR_ALPHA":"",e.vertexUv1s?"#define USE_UV1":"",e.vertexUv2s?"#define USE_UV2":"",e.vertexUv3s?"#define USE_UV3":"",e.pointsUvs?"#define USE_POINTS_UV":"",e.flatShading?"#define FLAT_SHADED":"",e.skinning?"#define USE_SKINNING":"",e.morphTargets?"#define USE_MORPHTARGETS":"",e.morphNormals&&e.flatShading===!1?"#define USE_MORPHNORMALS":"",e.morphColors&&e.isWebGL2?"#define USE_MORPHCOLORS":"",e.morphTargetsCount>0&&e.isWebGL2?"#define MORPHTARGETS_TEXTURE":"",e.morphTargetsCount>0&&e.isWebGL2?"#define MORPHTARGETS_TEXTURE_STRIDE "+e.morphTextureStride:"",e.morphTargetsCount>0&&e.isWebGL2?"#define MORPHTARGETS_COUNT "+e.morphTargetsCount:"",e.doubleSided?"#define DOUBLE_SIDED":"",e.flipSided?"#define FLIP_SIDED":"",e.shadowMapEnabled?"#define USE_SHADOWMAP":"",e.shadowMapEnabled?"#define "+l:"",e.sizeAttenuation?"#define USE_SIZEATTENUATION":"",e.numLightProbes>0?"#define USE_LIGHT_PROBES":"",e.useLegacyLights?"#define LEGACY_LIGHTS":"",e.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",e.logarithmicDepthBuffer&&e.rendererExtensionFragDepth?"#define USE_LOGDEPTHBUF_EXT":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#if ( defined( USE_MORPHTARGETS ) && ! defined( MORPHTARGETS_TEXTURE ) )","	attribute vec3 morphTarget0;","	attribute vec3 morphTarget1;","	attribute vec3 morphTarget2;","	attribute vec3 morphTarget3;","	#ifdef USE_MORPHNORMALS","		attribute vec3 morphNormal0;","		attribute vec3 morphNormal1;","		attribute vec3 morphNormal2;","		attribute vec3 morphNormal3;","	#else","		attribute vec3 morphTarget4;","		attribute vec3 morphTarget5;","		attribute vec3 morphTarget6;","		attribute vec3 morphTarget7;","	#endif","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(ti).join(`
`),y=[m,so(e),"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,M,e.useFog&&e.fog?"#define USE_FOG":"",e.useFog&&e.fogExp2?"#define FOG_EXP2":"",e.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",e.map?"#define USE_MAP":"",e.matcap?"#define USE_MATCAP":"",e.envMap?"#define USE_ENVMAP":"",e.envMap?"#define "+c:"",e.envMap?"#define "+h:"",e.envMap?"#define "+u:"",d?"#define CUBEUV_TEXEL_WIDTH "+d.texelWidth:"",d?"#define CUBEUV_TEXEL_HEIGHT "+d.texelHeight:"",d?"#define CUBEUV_MAX_MIP "+d.maxMip+".0":"",e.lightMap?"#define USE_LIGHTMAP":"",e.aoMap?"#define USE_AOMAP":"",e.bumpMap?"#define USE_BUMPMAP":"",e.normalMap?"#define USE_NORMALMAP":"",e.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",e.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",e.emissiveMap?"#define USE_EMISSIVEMAP":"",e.anisotropy?"#define USE_ANISOTROPY":"",e.anisotropyMap?"#define USE_ANISOTROPYMAP":"",e.clearcoat?"#define USE_CLEARCOAT":"",e.clearcoatMap?"#define USE_CLEARCOATMAP":"",e.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",e.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",e.iridescence?"#define USE_IRIDESCENCE":"",e.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",e.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",e.specularMap?"#define USE_SPECULARMAP":"",e.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",e.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",e.roughnessMap?"#define USE_ROUGHNESSMAP":"",e.metalnessMap?"#define USE_METALNESSMAP":"",e.alphaMap?"#define USE_ALPHAMAP":"",e.alphaTest?"#define USE_ALPHATEST":"",e.alphaHash?"#define USE_ALPHAHASH":"",e.sheen?"#define USE_SHEEN":"",e.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",e.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",e.transmission?"#define USE_TRANSMISSION":"",e.transmissionMap?"#define USE_TRANSMISSIONMAP":"",e.thicknessMap?"#define USE_THICKNESSMAP":"",e.vertexTangents&&e.flatShading===!1?"#define USE_TANGENT":"",e.vertexColors||e.instancingColor?"#define USE_COLOR":"",e.vertexAlphas?"#define USE_COLOR_ALPHA":"",e.vertexUv1s?"#define USE_UV1":"",e.vertexUv2s?"#define USE_UV2":"",e.vertexUv3s?"#define USE_UV3":"",e.pointsUvs?"#define USE_POINTS_UV":"",e.gradientMap?"#define USE_GRADIENTMAP":"",e.flatShading?"#define FLAT_SHADED":"",e.doubleSided?"#define DOUBLE_SIDED":"",e.flipSided?"#define FLIP_SIDED":"",e.shadowMapEnabled?"#define USE_SHADOWMAP":"",e.shadowMapEnabled?"#define "+l:"",e.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",e.numLightProbes>0?"#define USE_LIGHT_PROBES":"",e.useLegacyLights?"#define LEGACY_LIGHTS":"",e.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",e.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",e.logarithmicDepthBuffer&&e.rendererExtensionFragDepth?"#define USE_LOGDEPTHBUF_EXT":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",e.toneMapping!==un?"#define TONE_MAPPING":"",e.toneMapping!==un?Ot.tonemapping_pars_fragment:"",e.toneMapping!==un?lp("toneMapping",e.toneMapping):"",e.dithering?"#define DITHERING":"",e.opaque?"#define OPAQUE":"",Ot.colorspace_pars_fragment,op("linearToOutputTexel",e.outputColorSpace),e.useDepthPacking?"#define DEPTH_PACKING "+e.depthPacking:"",`
`].filter(ti).join(`
`)),o=vs(o),o=no(o,e),o=io(o,e),a=vs(a),a=no(a,e),a=io(a,e),o=ro(o),a=ro(a),e.isWebGL2&&e.isRawShaderMaterial!==!0&&(g=`#version 300 es
`,f=[_,"precision mediump sampler2DArray;","#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+f,y=["precision mediump sampler2DArray;","#define varying in",e.glslVersion===Sa?"":"layout(location = 0) out highp vec4 pc_fragColor;",e.glslVersion===Sa?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+y);const E=g+f+o,P=g+y+a,w=to(r,r.VERTEX_SHADER,E),b=to(r,r.FRAGMENT_SHADER,P);r.attachShader(p,w),r.attachShader(p,b),e.index0AttributeName!==void 0?r.bindAttribLocation(p,0,e.index0AttributeName):e.morphTargets===!0&&r.bindAttribLocation(p,0,"position"),r.linkProgram(p);function U(Z){if(i.debug.checkShaderErrors){const K=r.getProgramInfoLog(p).trim(),L=r.getShaderInfoLog(w).trim(),k=r.getShaderInfoLog(b).trim();let z=!0,J=!0;if(r.getProgramParameter(p,r.LINK_STATUS)===!1)if(z=!1,typeof i.debug.onShaderError=="function")i.debug.onShaderError(r,p,w,b);else{const X=eo(r,w,"vertex"),q=eo(r,b,"fragment");console.error("THREE.WebGLProgram: Shader Error "+r.getError()+" - VALIDATE_STATUS "+r.getProgramParameter(p,r.VALIDATE_STATUS)+`

Material Name: `+Z.name+`
Material Type: `+Z.type+`

Program Info Log: `+K+`
`+X+`
`+q)}else K!==""?console.warn("THREE.WebGLProgram: Program Info Log:",K):(L===""||k==="")&&(J=!1);J&&(Z.diagnostics={runnable:z,programLog:K,vertexShader:{log:L,prefix:f},fragmentShader:{log:k,prefix:y}})}r.deleteShader(w),r.deleteShader(b),V=new or(r,p),v=fp(r,p)}let V;this.getUniforms=function(){return V===void 0&&U(this),V};let v;this.getAttributes=function(){return v===void 0&&U(this),v};let A=e.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return A===!1&&(A=r.getProgramParameter(p,ip)),A},this.destroy=function(){n.releaseStatesOfProgram(this),r.deleteProgram(p),this.program=void 0},this.type=e.shaderType,this.name=e.shaderName,this.id=rp++,this.cacheKey=t,this.usedTimes=1,this.program=p,this.vertexShader=w,this.fragmentShader=b,this}let Tp=0;class Ap{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(t){const e=t.vertexShader,n=t.fragmentShader,r=this._getShaderStage(e),s=this._getShaderStage(n),o=this._getShaderCacheForMaterial(t);return o.has(r)===!1&&(o.add(r),r.usedTimes++),o.has(s)===!1&&(o.add(s),s.usedTimes++),this}remove(t){const e=this.materialCache.get(t);for(const n of e)n.usedTimes--,n.usedTimes===0&&this.shaderCache.delete(n.code);return this.materialCache.delete(t),this}getVertexShaderID(t){return this._getShaderStage(t.vertexShader).id}getFragmentShaderID(t){return this._getShaderStage(t.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(t){const e=this.materialCache;let n=e.get(t);return n===void 0&&(n=new Set,e.set(t,n)),n}_getShaderStage(t){const e=this.shaderCache;let n=e.get(t);return n===void 0&&(n=new bp(t),e.set(t,n)),n}}class bp{constructor(t){this.id=Tp++,this.code=t,this.usedTimes=0}}function wp(i,t,e,n,r,s,o){const a=new Rs,l=new Ap,c=new Set,h=[],u=r.isWebGL2,d=r.logarithmicDepthBuffer,m=r.vertexTextures;let _=r.precision;const M={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function p(v){return c.add(v),v===0?"uv":`uv${v}`}function f(v,A,Z,K,L){const k=K.fog,z=L.geometry,J=v.isMeshStandardMaterial?K.environment:null,X=(v.isMeshStandardMaterial?e:t).get(v.envMap||J),q=X&&X.mapping===mr?X.image.height:null,nt=M[v.type];v.precision!==null&&(_=r.getMaxPrecision(v.precision),_!==v.precision&&console.warn("THREE.WebGLProgram.getParameters:",v.precision,"not supported, using",_,"instead."));const et=z.morphAttributes.position||z.morphAttributes.normal||z.morphAttributes.color,gt=et!==void 0?et.length:0;let Pt=0;z.morphAttributes.position!==void 0&&(Pt=1),z.morphAttributes.normal!==void 0&&(Pt=2),z.morphAttributes.color!==void 0&&(Pt=3);let G,Q,pt,Tt;if(nt){const Zt=Ge[nt];G=Zt.vertexShader,Q=Zt.fragmentShader}else G=v.vertexShader,Q=v.fragmentShader,l.update(v),pt=l.getVertexShaderID(v),Tt=l.getFragmentShaderID(v);const Mt=i.getRenderTarget(),vt=L.isInstancedMesh===!0,Gt=L.isBatchedMesh===!0,At=!!v.map,R=!!v.matcap,at=!!X,Y=!!v.aoMap,rt=!!v.lightMap,$=!!v.bumpMap,_t=!!v.normalMap,dt=!!v.displacementMap,xt=!!v.emissiveMap,Vt=!!v.metalnessMap,T=!!v.roughnessMap,x=v.anisotropy>0,H=v.clearcoat>0,W=v.iridescence>0,tt=v.sheen>0,j=v.transmission>0,Lt=x&&!!v.anisotropyMap,wt=H&&!!v.clearcoatMap,lt=H&&!!v.clearcoatNormalMap,ht=H&&!!v.clearcoatRoughnessMap,Dt=W&&!!v.iridescenceMap,st=W&&!!v.iridescenceThicknessMap,re=tt&&!!v.sheenColorMap,kt=tt&&!!v.sheenRoughnessMap,bt=!!v.specularMap,St=!!v.specularColorMap,yt=!!v.specularIntensityMap,Xt=j&&!!v.transmissionMap,It=j&&!!v.thicknessMap,jt=!!v.gradientMap,D=!!v.alphaMap,ut=v.alphaTest>0,F=!!v.alphaHash,ot=!!v.extensions;let ft=un;v.toneMapped&&(Mt===null||Mt.isXRRenderTarget===!0)&&(ft=i.toneMapping);const Wt={isWebGL2:u,shaderID:nt,shaderType:v.type,shaderName:v.name,vertexShader:G,fragmentShader:Q,defines:v.defines,customVertexShaderID:pt,customFragmentShaderID:Tt,isRawShaderMaterial:v.isRawShaderMaterial===!0,glslVersion:v.glslVersion,precision:_,batching:Gt,instancing:vt,instancingColor:vt&&L.instanceColor!==null,instancingMorph:vt&&L.morphTexture!==null,supportsVertexTextures:m,outputColorSpace:Mt===null?i.outputColorSpace:Mt.isXRRenderTarget===!0?Mt.texture.colorSpace:mn,alphaToCoverage:!!v.alphaToCoverage,map:At,matcap:R,envMap:at,envMapMode:at&&X.mapping,envMapCubeUVHeight:q,aoMap:Y,lightMap:rt,bumpMap:$,normalMap:_t,displacementMap:m&&dt,emissiveMap:xt,normalMapObjectSpace:_t&&v.normalMapType===xc,normalMapTangentSpace:_t&&v.normalMapType===Go,metalnessMap:Vt,roughnessMap:T,anisotropy:x,anisotropyMap:Lt,clearcoat:H,clearcoatMap:wt,clearcoatNormalMap:lt,clearcoatRoughnessMap:ht,iridescence:W,iridescenceMap:Dt,iridescenceThicknessMap:st,sheen:tt,sheenColorMap:re,sheenRoughnessMap:kt,specularMap:bt,specularColorMap:St,specularIntensityMap:yt,transmission:j,transmissionMap:Xt,thicknessMap:It,gradientMap:jt,opaque:v.transparent===!1&&v.blending===ni&&v.alphaToCoverage===!1,alphaMap:D,alphaTest:ut,alphaHash:F,combine:v.combine,mapUv:At&&p(v.map.channel),aoMapUv:Y&&p(v.aoMap.channel),lightMapUv:rt&&p(v.lightMap.channel),bumpMapUv:$&&p(v.bumpMap.channel),normalMapUv:_t&&p(v.normalMap.channel),displacementMapUv:dt&&p(v.displacementMap.channel),emissiveMapUv:xt&&p(v.emissiveMap.channel),metalnessMapUv:Vt&&p(v.metalnessMap.channel),roughnessMapUv:T&&p(v.roughnessMap.channel),anisotropyMapUv:Lt&&p(v.anisotropyMap.channel),clearcoatMapUv:wt&&p(v.clearcoatMap.channel),clearcoatNormalMapUv:lt&&p(v.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:ht&&p(v.clearcoatRoughnessMap.channel),iridescenceMapUv:Dt&&p(v.iridescenceMap.channel),iridescenceThicknessMapUv:st&&p(v.iridescenceThicknessMap.channel),sheenColorMapUv:re&&p(v.sheenColorMap.channel),sheenRoughnessMapUv:kt&&p(v.sheenRoughnessMap.channel),specularMapUv:bt&&p(v.specularMap.channel),specularColorMapUv:St&&p(v.specularColorMap.channel),specularIntensityMapUv:yt&&p(v.specularIntensityMap.channel),transmissionMapUv:Xt&&p(v.transmissionMap.channel),thicknessMapUv:It&&p(v.thicknessMap.channel),alphaMapUv:D&&p(v.alphaMap.channel),vertexTangents:!!z.attributes.tangent&&(_t||x),vertexColors:v.vertexColors,vertexAlphas:v.vertexColors===!0&&!!z.attributes.color&&z.attributes.color.itemSize===4,pointsUvs:L.isPoints===!0&&!!z.attributes.uv&&(At||D),fog:!!k,useFog:v.fog===!0,fogExp2:!!k&&k.isFogExp2,flatShading:v.flatShading===!0,sizeAttenuation:v.sizeAttenuation===!0,logarithmicDepthBuffer:d,skinning:L.isSkinnedMesh===!0,morphTargets:z.morphAttributes.position!==void 0,morphNormals:z.morphAttributes.normal!==void 0,morphColors:z.morphAttributes.color!==void 0,morphTargetsCount:gt,morphTextureStride:Pt,numDirLights:A.directional.length,numPointLights:A.point.length,numSpotLights:A.spot.length,numSpotLightMaps:A.spotLightMap.length,numRectAreaLights:A.rectArea.length,numHemiLights:A.hemi.length,numDirLightShadows:A.directionalShadowMap.length,numPointLightShadows:A.pointShadowMap.length,numSpotLightShadows:A.spotShadowMap.length,numSpotLightShadowsWithMaps:A.numSpotLightShadowsWithMaps,numLightProbes:A.numLightProbes,numClippingPlanes:o.numPlanes,numClipIntersection:o.numIntersection,dithering:v.dithering,shadowMapEnabled:i.shadowMap.enabled&&Z.length>0,shadowMapType:i.shadowMap.type,toneMapping:ft,useLegacyLights:i._useLegacyLights,decodeVideoTexture:At&&v.map.isVideoTexture===!0&&Yt.getTransfer(v.map.colorSpace)===$t,premultipliedAlpha:v.premultipliedAlpha,doubleSided:v.side===je,flipSided:v.side===Ee,useDepthPacking:v.depthPacking>=0,depthPacking:v.depthPacking||0,index0AttributeName:v.index0AttributeName,extensionDerivatives:ot&&v.extensions.derivatives===!0,extensionFragDepth:ot&&v.extensions.fragDepth===!0,extensionDrawBuffers:ot&&v.extensions.drawBuffers===!0,extensionShaderTextureLOD:ot&&v.extensions.shaderTextureLOD===!0,extensionClipCullDistance:ot&&v.extensions.clipCullDistance===!0&&n.has("WEBGL_clip_cull_distance"),extensionMultiDraw:ot&&v.extensions.multiDraw===!0&&n.has("WEBGL_multi_draw"),rendererExtensionFragDepth:u||n.has("EXT_frag_depth"),rendererExtensionDrawBuffers:u||n.has("WEBGL_draw_buffers"),rendererExtensionShaderTextureLod:u||n.has("EXT_shader_texture_lod"),rendererExtensionParallelShaderCompile:n.has("KHR_parallel_shader_compile"),customProgramCacheKey:v.customProgramCacheKey()};return Wt.vertexUv1s=c.has(1),Wt.vertexUv2s=c.has(2),Wt.vertexUv3s=c.has(3),c.clear(),Wt}function y(v){const A=[];if(v.shaderID?A.push(v.shaderID):(A.push(v.customVertexShaderID),A.push(v.customFragmentShaderID)),v.defines!==void 0)for(const Z in v.defines)A.push(Z),A.push(v.defines[Z]);return v.isRawShaderMaterial===!1&&(g(A,v),E(A,v),A.push(i.outputColorSpace)),A.push(v.customProgramCacheKey),A.join()}function g(v,A){v.push(A.precision),v.push(A.outputColorSpace),v.push(A.envMapMode),v.push(A.envMapCubeUVHeight),v.push(A.mapUv),v.push(A.alphaMapUv),v.push(A.lightMapUv),v.push(A.aoMapUv),v.push(A.bumpMapUv),v.push(A.normalMapUv),v.push(A.displacementMapUv),v.push(A.emissiveMapUv),v.push(A.metalnessMapUv),v.push(A.roughnessMapUv),v.push(A.anisotropyMapUv),v.push(A.clearcoatMapUv),v.push(A.clearcoatNormalMapUv),v.push(A.clearcoatRoughnessMapUv),v.push(A.iridescenceMapUv),v.push(A.iridescenceThicknessMapUv),v.push(A.sheenColorMapUv),v.push(A.sheenRoughnessMapUv),v.push(A.specularMapUv),v.push(A.specularColorMapUv),v.push(A.specularIntensityMapUv),v.push(A.transmissionMapUv),v.push(A.thicknessMapUv),v.push(A.combine),v.push(A.fogExp2),v.push(A.sizeAttenuation),v.push(A.morphTargetsCount),v.push(A.morphAttributeCount),v.push(A.numDirLights),v.push(A.numPointLights),v.push(A.numSpotLights),v.push(A.numSpotLightMaps),v.push(A.numHemiLights),v.push(A.numRectAreaLights),v.push(A.numDirLightShadows),v.push(A.numPointLightShadows),v.push(A.numSpotLightShadows),v.push(A.numSpotLightShadowsWithMaps),v.push(A.numLightProbes),v.push(A.shadowMapType),v.push(A.toneMapping),v.push(A.numClippingPlanes),v.push(A.numClipIntersection),v.push(A.depthPacking)}function E(v,A){a.disableAll(),A.isWebGL2&&a.enable(0),A.supportsVertexTextures&&a.enable(1),A.instancing&&a.enable(2),A.instancingColor&&a.enable(3),A.instancingMorph&&a.enable(4),A.matcap&&a.enable(5),A.envMap&&a.enable(6),A.normalMapObjectSpace&&a.enable(7),A.normalMapTangentSpace&&a.enable(8),A.clearcoat&&a.enable(9),A.iridescence&&a.enable(10),A.alphaTest&&a.enable(11),A.vertexColors&&a.enable(12),A.vertexAlphas&&a.enable(13),A.vertexUv1s&&a.enable(14),A.vertexUv2s&&a.enable(15),A.vertexUv3s&&a.enable(16),A.vertexTangents&&a.enable(17),A.anisotropy&&a.enable(18),A.alphaHash&&a.enable(19),A.batching&&a.enable(20),v.push(a.mask),a.disableAll(),A.fog&&a.enable(0),A.useFog&&a.enable(1),A.flatShading&&a.enable(2),A.logarithmicDepthBuffer&&a.enable(3),A.skinning&&a.enable(4),A.morphTargets&&a.enable(5),A.morphNormals&&a.enable(6),A.morphColors&&a.enable(7),A.premultipliedAlpha&&a.enable(8),A.shadowMapEnabled&&a.enable(9),A.useLegacyLights&&a.enable(10),A.doubleSided&&a.enable(11),A.flipSided&&a.enable(12),A.useDepthPacking&&a.enable(13),A.dithering&&a.enable(14),A.transmission&&a.enable(15),A.sheen&&a.enable(16),A.opaque&&a.enable(17),A.pointsUvs&&a.enable(18),A.decodeVideoTexture&&a.enable(19),A.alphaToCoverage&&a.enable(20),v.push(a.mask)}function P(v){const A=M[v.type];let Z;if(A){const K=Ge[A];Z=ah.clone(K.uniforms)}else Z=v.uniforms;return Z}function w(v,A){let Z;for(let K=0,L=h.length;K<L;K++){const k=h[K];if(k.cacheKey===A){Z=k,++Z.usedTimes;break}}return Z===void 0&&(Z=new Ep(i,A,v,s),h.push(Z)),Z}function b(v){if(--v.usedTimes===0){const A=h.indexOf(v);h[A]=h[h.length-1],h.pop(),v.destroy()}}function U(v){l.remove(v)}function V(){l.dispose()}return{getParameters:f,getProgramCacheKey:y,getUniforms:P,acquireProgram:w,releaseProgram:b,releaseShaderCache:U,programs:h,dispose:V}}function Rp(){let i=new WeakMap;function t(s){let o=i.get(s);return o===void 0&&(o={},i.set(s,o)),o}function e(s){i.delete(s)}function n(s,o,a){i.get(s)[o]=a}function r(){i=new WeakMap}return{get:t,remove:e,update:n,dispose:r}}function Cp(i,t){return i.groupOrder!==t.groupOrder?i.groupOrder-t.groupOrder:i.renderOrder!==t.renderOrder?i.renderOrder-t.renderOrder:i.material.id!==t.material.id?i.material.id-t.material.id:i.z!==t.z?i.z-t.z:i.id-t.id}function ao(i,t){return i.groupOrder!==t.groupOrder?i.groupOrder-t.groupOrder:i.renderOrder!==t.renderOrder?i.renderOrder-t.renderOrder:i.z!==t.z?t.z-i.z:i.id-t.id}function oo(){const i=[];let t=0;const e=[],n=[],r=[];function s(){t=0,e.length=0,n.length=0,r.length=0}function o(u,d,m,_,M,p){let f=i[t];return f===void 0?(f={id:u.id,object:u,geometry:d,material:m,groupOrder:_,renderOrder:u.renderOrder,z:M,group:p},i[t]=f):(f.id=u.id,f.object=u,f.geometry=d,f.material=m,f.groupOrder=_,f.renderOrder=u.renderOrder,f.z=M,f.group=p),t++,f}function a(u,d,m,_,M,p){const f=o(u,d,m,_,M,p);m.transmission>0?n.push(f):m.transparent===!0?r.push(f):e.push(f)}function l(u,d,m,_,M,p){const f=o(u,d,m,_,M,p);m.transmission>0?n.unshift(f):m.transparent===!0?r.unshift(f):e.unshift(f)}function c(u,d){e.length>1&&e.sort(u||Cp),n.length>1&&n.sort(d||ao),r.length>1&&r.sort(d||ao)}function h(){for(let u=t,d=i.length;u<d;u++){const m=i[u];if(m.id===null)break;m.id=null,m.object=null,m.geometry=null,m.material=null,m.group=null}}return{opaque:e,transmissive:n,transparent:r,init:s,push:a,unshift:l,finish:h,sort:c}}function Pp(){let i=new WeakMap;function t(n,r){const s=i.get(n);let o;return s===void 0?(o=new oo,i.set(n,[o])):r>=s.length?(o=new oo,s.push(o)):o=s[r],o}function e(){i=new WeakMap}return{get:t,dispose:e}}function Lp(){const i={};return{get:function(t){if(i[t.id]!==void 0)return i[t.id];let e;switch(t.type){case"DirectionalLight":e={direction:new C,color:new zt};break;case"SpotLight":e={position:new C,direction:new C,color:new zt,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":e={position:new C,color:new zt,distance:0,decay:0};break;case"HemisphereLight":e={direction:new C,skyColor:new zt,groundColor:new zt};break;case"RectAreaLight":e={color:new zt,position:new C,halfWidth:new C,halfHeight:new C};break}return i[t.id]=e,e}}}function Dp(){const i={};return{get:function(t){if(i[t.id]!==void 0)return i[t.id];let e;switch(t.type){case"DirectionalLight":e={shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new it};break;case"SpotLight":e={shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new it};break;case"PointLight":e={shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new it,shadowCameraNear:1,shadowCameraFar:1e3};break}return i[t.id]=e,e}}}let Up=0;function Ip(i,t){return(t.castShadow?2:0)-(i.castShadow?2:0)+(t.map?1:0)-(i.map?1:0)}function Np(i,t){const e=new Lp,n=Dp(),r={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let h=0;h<9;h++)r.probe.push(new C);const s=new C,o=new Jt,a=new Jt;function l(h,u){let d=0,m=0,_=0;for(let Z=0;Z<9;Z++)r.probe[Z].set(0,0,0);let M=0,p=0,f=0,y=0,g=0,E=0,P=0,w=0,b=0,U=0,V=0;h.sort(Ip);const v=u===!0?Math.PI:1;for(let Z=0,K=h.length;Z<K;Z++){const L=h[Z],k=L.color,z=L.intensity,J=L.distance,X=L.shadow&&L.shadow.map?L.shadow.map.texture:null;if(L.isAmbientLight)d+=k.r*z*v,m+=k.g*z*v,_+=k.b*z*v;else if(L.isLightProbe){for(let q=0;q<9;q++)r.probe[q].addScaledVector(L.sh.coefficients[q],z);V++}else if(L.isDirectionalLight){const q=e.get(L);if(q.color.copy(L.color).multiplyScalar(L.intensity*v),L.castShadow){const nt=L.shadow,et=n.get(L);et.shadowBias=nt.bias,et.shadowNormalBias=nt.normalBias,et.shadowRadius=nt.radius,et.shadowMapSize=nt.mapSize,r.directionalShadow[M]=et,r.directionalShadowMap[M]=X,r.directionalShadowMatrix[M]=L.shadow.matrix,E++}r.directional[M]=q,M++}else if(L.isSpotLight){const q=e.get(L);q.position.setFromMatrixPosition(L.matrixWorld),q.color.copy(k).multiplyScalar(z*v),q.distance=J,q.coneCos=Math.cos(L.angle),q.penumbraCos=Math.cos(L.angle*(1-L.penumbra)),q.decay=L.decay,r.spot[f]=q;const nt=L.shadow;if(L.map&&(r.spotLightMap[b]=L.map,b++,nt.updateMatrices(L),L.castShadow&&U++),r.spotLightMatrix[f]=nt.matrix,L.castShadow){const et=n.get(L);et.shadowBias=nt.bias,et.shadowNormalBias=nt.normalBias,et.shadowRadius=nt.radius,et.shadowMapSize=nt.mapSize,r.spotShadow[f]=et,r.spotShadowMap[f]=X,w++}f++}else if(L.isRectAreaLight){const q=e.get(L);q.color.copy(k).multiplyScalar(z),q.halfWidth.set(L.width*.5,0,0),q.halfHeight.set(0,L.height*.5,0),r.rectArea[y]=q,y++}else if(L.isPointLight){const q=e.get(L);if(q.color.copy(L.color).multiplyScalar(L.intensity*v),q.distance=L.distance,q.decay=L.decay,L.castShadow){const nt=L.shadow,et=n.get(L);et.shadowBias=nt.bias,et.shadowNormalBias=nt.normalBias,et.shadowRadius=nt.radius,et.shadowMapSize=nt.mapSize,et.shadowCameraNear=nt.camera.near,et.shadowCameraFar=nt.camera.far,r.pointShadow[p]=et,r.pointShadowMap[p]=X,r.pointShadowMatrix[p]=L.shadow.matrix,P++}r.point[p]=q,p++}else if(L.isHemisphereLight){const q=e.get(L);q.skyColor.copy(L.color).multiplyScalar(z*v),q.groundColor.copy(L.groundColor).multiplyScalar(z*v),r.hemi[g]=q,g++}}y>0&&(t.isWebGL2?i.has("OES_texture_float_linear")===!0?(r.rectAreaLTC1=ct.LTC_FLOAT_1,r.rectAreaLTC2=ct.LTC_FLOAT_2):(r.rectAreaLTC1=ct.LTC_HALF_1,r.rectAreaLTC2=ct.LTC_HALF_2):i.has("OES_texture_float_linear")===!0?(r.rectAreaLTC1=ct.LTC_FLOAT_1,r.rectAreaLTC2=ct.LTC_FLOAT_2):i.has("OES_texture_half_float_linear")===!0?(r.rectAreaLTC1=ct.LTC_HALF_1,r.rectAreaLTC2=ct.LTC_HALF_2):console.error("THREE.WebGLRenderer: Unable to use RectAreaLight. Missing WebGL extensions.")),r.ambient[0]=d,r.ambient[1]=m,r.ambient[2]=_;const A=r.hash;(A.directionalLength!==M||A.pointLength!==p||A.spotLength!==f||A.rectAreaLength!==y||A.hemiLength!==g||A.numDirectionalShadows!==E||A.numPointShadows!==P||A.numSpotShadows!==w||A.numSpotMaps!==b||A.numLightProbes!==V)&&(r.directional.length=M,r.spot.length=f,r.rectArea.length=y,r.point.length=p,r.hemi.length=g,r.directionalShadow.length=E,r.directionalShadowMap.length=E,r.pointShadow.length=P,r.pointShadowMap.length=P,r.spotShadow.length=w,r.spotShadowMap.length=w,r.directionalShadowMatrix.length=E,r.pointShadowMatrix.length=P,r.spotLightMatrix.length=w+b-U,r.spotLightMap.length=b,r.numSpotLightShadowsWithMaps=U,r.numLightProbes=V,A.directionalLength=M,A.pointLength=p,A.spotLength=f,A.rectAreaLength=y,A.hemiLength=g,A.numDirectionalShadows=E,A.numPointShadows=P,A.numSpotShadows=w,A.numSpotMaps=b,A.numLightProbes=V,r.version=Up++)}function c(h,u){let d=0,m=0,_=0,M=0,p=0;const f=u.matrixWorldInverse;for(let y=0,g=h.length;y<g;y++){const E=h[y];if(E.isDirectionalLight){const P=r.directional[d];P.direction.setFromMatrixPosition(E.matrixWorld),s.setFromMatrixPosition(E.target.matrixWorld),P.direction.sub(s),P.direction.transformDirection(f),d++}else if(E.isSpotLight){const P=r.spot[_];P.position.setFromMatrixPosition(E.matrixWorld),P.position.applyMatrix4(f),P.direction.setFromMatrixPosition(E.matrixWorld),s.setFromMatrixPosition(E.target.matrixWorld),P.direction.sub(s),P.direction.transformDirection(f),_++}else if(E.isRectAreaLight){const P=r.rectArea[M];P.position.setFromMatrixPosition(E.matrixWorld),P.position.applyMatrix4(f),a.identity(),o.copy(E.matrixWorld),o.premultiply(f),a.extractRotation(o),P.halfWidth.set(E.width*.5,0,0),P.halfHeight.set(0,E.height*.5,0),P.halfWidth.applyMatrix4(a),P.halfHeight.applyMatrix4(a),M++}else if(E.isPointLight){const P=r.point[m];P.position.setFromMatrixPosition(E.matrixWorld),P.position.applyMatrix4(f),m++}else if(E.isHemisphereLight){const P=r.hemi[p];P.direction.setFromMatrixPosition(E.matrixWorld),P.direction.transformDirection(f),p++}}}return{setup:l,setupView:c,state:r}}function lo(i,t){const e=new Np(i,t),n=[],r=[];function s(){n.length=0,r.length=0}function o(u){n.push(u)}function a(u){r.push(u)}function l(u){e.setup(n,u)}function c(u){e.setupView(n,u)}return{init:s,state:{lightsArray:n,shadowsArray:r,lights:e},setupLights:l,setupLightsView:c,pushLight:o,pushShadow:a}}function Fp(i,t){let e=new WeakMap;function n(s,o=0){const a=e.get(s);let l;return a===void 0?(l=new lo(i,t),e.set(s,[l])):o>=a.length?(l=new lo(i,t),a.push(l)):l=a[o],l}function r(){e=new WeakMap}return{get:n,dispose:r}}class Op extends hi{constructor(t){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=_c,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(t)}copy(t){return super.copy(t),this.depthPacking=t.depthPacking,this.map=t.map,this.alphaMap=t.alphaMap,this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this}}class Bp extends hi{constructor(t){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(t)}copy(t){return super.copy(t),this.map=t.map,this.alphaMap=t.alphaMap,this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this}}const zp=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,Gp=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
#include <packing>
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = unpackRGBATo2Half( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ) );
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = unpackRGBAToDepth( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ) );
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( squared_mean - mean * mean );
	gl_FragColor = pack2HalfToRGBA( vec2( mean, std_dev ) );
}`;function Hp(i,t,e){let n=new Cs;const r=new it,s=new it,o=new te,a=new Op({depthPacking:vc}),l=new Bp,c={},h=e.maxTextureSize,u={[pn]:Ee,[Ee]:pn,[je]:je},d=new tn({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new it},radius:{value:4}},vertexShader:zp,fragmentShader:Gp}),m=d.clone();m.defines.HORIZONTAL_PASS=1;const _=new pe;_.setAttribute("position",new Le(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));const M=new Oe(_,d),p=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=Co;let f=this.type;this.render=function(w,b,U){if(p.enabled===!1||p.autoUpdate===!1&&p.needsUpdate===!1||w.length===0)return;const V=i.getRenderTarget(),v=i.getActiveCubeFace(),A=i.getActiveMipmapLevel(),Z=i.state;Z.setBlending(hn),Z.buffers.color.setClear(1,1,1,1),Z.buffers.depth.setTest(!0),Z.setScissorTest(!1);const K=f!==$e&&this.type===$e,L=f===$e&&this.type!==$e;for(let k=0,z=w.length;k<z;k++){const J=w[k],X=J.shadow;if(X===void 0){console.warn("THREE.WebGLShadowMap:",J,"has no shadow.");continue}if(X.autoUpdate===!1&&X.needsUpdate===!1)continue;r.copy(X.mapSize);const q=X.getFrameExtents();if(r.multiply(q),s.copy(X.mapSize),(r.x>h||r.y>h)&&(r.x>h&&(s.x=Math.floor(h/q.x),r.x=s.x*q.x,X.mapSize.x=s.x),r.y>h&&(s.y=Math.floor(h/q.y),r.y=s.y*q.y,X.mapSize.y=s.y)),X.map===null||K===!0||L===!0){const et=this.type!==$e?{minFilter:de,magFilter:de}:{};X.map!==null&&X.map.dispose(),X.map=new Ln(r.x,r.y,et),X.map.texture.name=J.name+".shadowMap",X.camera.updateProjectionMatrix()}i.setRenderTarget(X.map),i.clear();const nt=X.getViewportCount();for(let et=0;et<nt;et++){const gt=X.getViewport(et);o.set(s.x*gt.x,s.y*gt.y,s.x*gt.z,s.y*gt.w),Z.viewport(o),X.updateMatrices(J,et),n=X.getFrustum(),E(b,U,X.camera,J,this.type)}X.isPointLightShadow!==!0&&this.type===$e&&y(X,U),X.needsUpdate=!1}f=this.type,p.needsUpdate=!1,i.setRenderTarget(V,v,A)};function y(w,b){const U=t.update(M);d.defines.VSM_SAMPLES!==w.blurSamples&&(d.defines.VSM_SAMPLES=w.blurSamples,m.defines.VSM_SAMPLES=w.blurSamples,d.needsUpdate=!0,m.needsUpdate=!0),w.mapPass===null&&(w.mapPass=new Ln(r.x,r.y)),d.uniforms.shadow_pass.value=w.map.texture,d.uniforms.resolution.value=w.mapSize,d.uniforms.radius.value=w.radius,i.setRenderTarget(w.mapPass),i.clear(),i.renderBufferDirect(b,null,U,d,M,null),m.uniforms.shadow_pass.value=w.mapPass.texture,m.uniforms.resolution.value=w.mapSize,m.uniforms.radius.value=w.radius,i.setRenderTarget(w.map),i.clear(),i.renderBufferDirect(b,null,U,m,M,null)}function g(w,b,U,V){let v=null;const A=U.isPointLight===!0?w.customDistanceMaterial:w.customDepthMaterial;if(A!==void 0)v=A;else if(v=U.isPointLight===!0?l:a,i.localClippingEnabled&&b.clipShadows===!0&&Array.isArray(b.clippingPlanes)&&b.clippingPlanes.length!==0||b.displacementMap&&b.displacementScale!==0||b.alphaMap&&b.alphaTest>0||b.map&&b.alphaTest>0){const Z=v.uuid,K=b.uuid;let L=c[Z];L===void 0&&(L={},c[Z]=L);let k=L[K];k===void 0&&(k=v.clone(),L[K]=k,b.addEventListener("dispose",P)),v=k}if(v.visible=b.visible,v.wireframe=b.wireframe,V===$e?v.side=b.shadowSide!==null?b.shadowSide:b.side:v.side=b.shadowSide!==null?b.shadowSide:u[b.side],v.alphaMap=b.alphaMap,v.alphaTest=b.alphaTest,v.map=b.map,v.clipShadows=b.clipShadows,v.clippingPlanes=b.clippingPlanes,v.clipIntersection=b.clipIntersection,v.displacementMap=b.displacementMap,v.displacementScale=b.displacementScale,v.displacementBias=b.displacementBias,v.wireframeLinewidth=b.wireframeLinewidth,v.linewidth=b.linewidth,U.isPointLight===!0&&v.isMeshDistanceMaterial===!0){const Z=i.properties.get(v);Z.light=U}return v}function E(w,b,U,V,v){if(w.visible===!1)return;if(w.layers.test(b.layers)&&(w.isMesh||w.isLine||w.isPoints)&&(w.castShadow||w.receiveShadow&&v===$e)&&(!w.frustumCulled||n.intersectsObject(w))){w.modelViewMatrix.multiplyMatrices(U.matrixWorldInverse,w.matrixWorld);const K=t.update(w),L=w.material;if(Array.isArray(L)){const k=K.groups;for(let z=0,J=k.length;z<J;z++){const X=k[z],q=L[X.materialIndex];if(q&&q.visible){const nt=g(w,q,V,v);w.onBeforeShadow(i,w,b,U,K,nt,X),i.renderBufferDirect(U,null,K,nt,w,X),w.onAfterShadow(i,w,b,U,K,nt,X)}}}else if(L.visible){const k=g(w,L,V,v);w.onBeforeShadow(i,w,b,U,K,k,null),i.renderBufferDirect(U,null,K,k,w,null),w.onAfterShadow(i,w,b,U,K,k,null)}}const Z=w.children;for(let K=0,L=Z.length;K<L;K++)E(Z[K],b,U,V,v)}function P(w){w.target.removeEventListener("dispose",P);for(const U in c){const V=c[U],v=w.target.uuid;v in V&&(V[v].dispose(),delete V[v])}}}function Vp(i,t,e){const n=e.isWebGL2;function r(){let D=!1;const ut=new te;let F=null;const ot=new te(0,0,0,0);return{setMask:function(ft){F!==ft&&!D&&(i.colorMask(ft,ft,ft,ft),F=ft)},setLocked:function(ft){D=ft},setClear:function(ft,Wt,Zt,fe,we){we===!0&&(ft*=fe,Wt*=fe,Zt*=fe),ut.set(ft,Wt,Zt,fe),ot.equals(ut)===!1&&(i.clearColor(ft,Wt,Zt,fe),ot.copy(ut))},reset:function(){D=!1,F=null,ot.set(-1,0,0,0)}}}function s(){let D=!1,ut=null,F=null,ot=null;return{setTest:function(ft){ft?vt(i.DEPTH_TEST):Gt(i.DEPTH_TEST)},setMask:function(ft){ut!==ft&&!D&&(i.depthMask(ft),ut=ft)},setFunc:function(ft){if(F!==ft){switch(ft){case Jl:i.depthFunc(i.NEVER);break;case Zl:i.depthFunc(i.ALWAYS);break;case Kl:i.depthFunc(i.LESS);break;case lr:i.depthFunc(i.LEQUAL);break;case $l:i.depthFunc(i.EQUAL);break;case jl:i.depthFunc(i.GEQUAL);break;case Ql:i.depthFunc(i.GREATER);break;case tc:i.depthFunc(i.NOTEQUAL);break;default:i.depthFunc(i.LEQUAL)}F=ft}},setLocked:function(ft){D=ft},setClear:function(ft){ot!==ft&&(i.clearDepth(ft),ot=ft)},reset:function(){D=!1,ut=null,F=null,ot=null}}}function o(){let D=!1,ut=null,F=null,ot=null,ft=null,Wt=null,Zt=null,fe=null,we=null;return{setTest:function(Kt){D||(Kt?vt(i.STENCIL_TEST):Gt(i.STENCIL_TEST))},setMask:function(Kt){ut!==Kt&&!D&&(i.stencilMask(Kt),ut=Kt)},setFunc:function(Kt,xe,Be){(F!==Kt||ot!==xe||ft!==Be)&&(i.stencilFunc(Kt,xe,Be),F=Kt,ot=xe,ft=Be)},setOp:function(Kt,xe,Be){(Wt!==Kt||Zt!==xe||fe!==Be)&&(i.stencilOp(Kt,xe,Be),Wt=Kt,Zt=xe,fe=Be)},setLocked:function(Kt){D=Kt},setClear:function(Kt){we!==Kt&&(i.clearStencil(Kt),we=Kt)},reset:function(){D=!1,ut=null,F=null,ot=null,ft=null,Wt=null,Zt=null,fe=null,we=null}}}const a=new r,l=new s,c=new o,h=new WeakMap,u=new WeakMap;let d={},m={},_=new WeakMap,M=[],p=null,f=!1,y=null,g=null,E=null,P=null,w=null,b=null,U=null,V=new zt(0,0,0),v=0,A=!1,Z=null,K=null,L=null,k=null,z=null;const J=i.getParameter(i.MAX_COMBINED_TEXTURE_IMAGE_UNITS);let X=!1,q=0;const nt=i.getParameter(i.VERSION);nt.indexOf("WebGL")!==-1?(q=parseFloat(/^WebGL (\d)/.exec(nt)[1]),X=q>=1):nt.indexOf("OpenGL ES")!==-1&&(q=parseFloat(/^OpenGL ES (\d)/.exec(nt)[1]),X=q>=2);let et=null,gt={};const Pt=i.getParameter(i.SCISSOR_BOX),G=i.getParameter(i.VIEWPORT),Q=new te().fromArray(Pt),pt=new te().fromArray(G);function Tt(D,ut,F,ot){const ft=new Uint8Array(4),Wt=i.createTexture();i.bindTexture(D,Wt),i.texParameteri(D,i.TEXTURE_MIN_FILTER,i.NEAREST),i.texParameteri(D,i.TEXTURE_MAG_FILTER,i.NEAREST);for(let Zt=0;Zt<F;Zt++)n&&(D===i.TEXTURE_3D||D===i.TEXTURE_2D_ARRAY)?i.texImage3D(ut,0,i.RGBA,1,1,ot,0,i.RGBA,i.UNSIGNED_BYTE,ft):i.texImage2D(ut+Zt,0,i.RGBA,1,1,0,i.RGBA,i.UNSIGNED_BYTE,ft);return Wt}const Mt={};Mt[i.TEXTURE_2D]=Tt(i.TEXTURE_2D,i.TEXTURE_2D,1),Mt[i.TEXTURE_CUBE_MAP]=Tt(i.TEXTURE_CUBE_MAP,i.TEXTURE_CUBE_MAP_POSITIVE_X,6),n&&(Mt[i.TEXTURE_2D_ARRAY]=Tt(i.TEXTURE_2D_ARRAY,i.TEXTURE_2D_ARRAY,1,1),Mt[i.TEXTURE_3D]=Tt(i.TEXTURE_3D,i.TEXTURE_3D,1,1)),a.setClear(0,0,0,1),l.setClear(1),c.setClear(0),vt(i.DEPTH_TEST),l.setFunc(lr),dt(!1),xt(Hs),vt(i.CULL_FACE),$(hn);function vt(D){d[D]!==!0&&(i.enable(D),d[D]=!0)}function Gt(D){d[D]!==!1&&(i.disable(D),d[D]=!1)}function At(D,ut){return m[D]!==ut?(i.bindFramebuffer(D,ut),m[D]=ut,n&&(D===i.DRAW_FRAMEBUFFER&&(m[i.FRAMEBUFFER]=ut),D===i.FRAMEBUFFER&&(m[i.DRAW_FRAMEBUFFER]=ut)),!0):!1}function R(D,ut){let F=M,ot=!1;if(D){F=_.get(ut),F===void 0&&(F=[],_.set(ut,F));const ft=D.textures;if(F.length!==ft.length||F[0]!==i.COLOR_ATTACHMENT0){for(let Wt=0,Zt=ft.length;Wt<Zt;Wt++)F[Wt]=i.COLOR_ATTACHMENT0+Wt;F.length=ft.length,ot=!0}}else F[0]!==i.BACK&&(F[0]=i.BACK,ot=!0);if(ot)if(e.isWebGL2)i.drawBuffers(F);else if(t.has("WEBGL_draw_buffers")===!0)t.get("WEBGL_draw_buffers").drawBuffersWEBGL(F);else throw new Error("THREE.WebGLState: Usage of gl.drawBuffers() require WebGL2 or WEBGL_draw_buffers extension")}function at(D){return p!==D?(i.useProgram(D),p=D,!0):!1}const Y={[bn]:i.FUNC_ADD,[Ul]:i.FUNC_SUBTRACT,[Il]:i.FUNC_REVERSE_SUBTRACT};if(n)Y[Xs]=i.MIN,Y[qs]=i.MAX;else{const D=t.get("EXT_blend_minmax");D!==null&&(Y[Xs]=D.MIN_EXT,Y[qs]=D.MAX_EXT)}const rt={[Nl]:i.ZERO,[Fl]:i.ONE,[Ol]:i.SRC_COLOR,[hs]:i.SRC_ALPHA,[kl]:i.SRC_ALPHA_SATURATE,[Hl]:i.DST_COLOR,[zl]:i.DST_ALPHA,[Bl]:i.ONE_MINUS_SRC_COLOR,[us]:i.ONE_MINUS_SRC_ALPHA,[Vl]:i.ONE_MINUS_DST_COLOR,[Gl]:i.ONE_MINUS_DST_ALPHA,[Wl]:i.CONSTANT_COLOR,[Xl]:i.ONE_MINUS_CONSTANT_COLOR,[ql]:i.CONSTANT_ALPHA,[Yl]:i.ONE_MINUS_CONSTANT_ALPHA};function $(D,ut,F,ot,ft,Wt,Zt,fe,we,Kt){if(D===hn){f===!0&&(Gt(i.BLEND),f=!1);return}if(f===!1&&(vt(i.BLEND),f=!0),D!==Dl){if(D!==y||Kt!==A){if((g!==bn||w!==bn)&&(i.blendEquation(i.FUNC_ADD),g=bn,w=bn),Kt)switch(D){case ni:i.blendFuncSeparate(i.ONE,i.ONE_MINUS_SRC_ALPHA,i.ONE,i.ONE_MINUS_SRC_ALPHA);break;case Vs:i.blendFunc(i.ONE,i.ONE);break;case ks:i.blendFuncSeparate(i.ZERO,i.ONE_MINUS_SRC_COLOR,i.ZERO,i.ONE);break;case Ws:i.blendFuncSeparate(i.ZERO,i.SRC_COLOR,i.ZERO,i.SRC_ALPHA);break;default:console.error("THREE.WebGLState: Invalid blending: ",D);break}else switch(D){case ni:i.blendFuncSeparate(i.SRC_ALPHA,i.ONE_MINUS_SRC_ALPHA,i.ONE,i.ONE_MINUS_SRC_ALPHA);break;case Vs:i.blendFunc(i.SRC_ALPHA,i.ONE);break;case ks:i.blendFuncSeparate(i.ZERO,i.ONE_MINUS_SRC_COLOR,i.ZERO,i.ONE);break;case Ws:i.blendFunc(i.ZERO,i.SRC_COLOR);break;default:console.error("THREE.WebGLState: Invalid blending: ",D);break}E=null,P=null,b=null,U=null,V.set(0,0,0),v=0,y=D,A=Kt}return}ft=ft||ut,Wt=Wt||F,Zt=Zt||ot,(ut!==g||ft!==w)&&(i.blendEquationSeparate(Y[ut],Y[ft]),g=ut,w=ft),(F!==E||ot!==P||Wt!==b||Zt!==U)&&(i.blendFuncSeparate(rt[F],rt[ot],rt[Wt],rt[Zt]),E=F,P=ot,b=Wt,U=Zt),(fe.equals(V)===!1||we!==v)&&(i.blendColor(fe.r,fe.g,fe.b,we),V.copy(fe),v=we),y=D,A=!1}function _t(D,ut){D.side===je?Gt(i.CULL_FACE):vt(i.CULL_FACE);let F=D.side===Ee;ut&&(F=!F),dt(F),D.blending===ni&&D.transparent===!1?$(hn):$(D.blending,D.blendEquation,D.blendSrc,D.blendDst,D.blendEquationAlpha,D.blendSrcAlpha,D.blendDstAlpha,D.blendColor,D.blendAlpha,D.premultipliedAlpha),l.setFunc(D.depthFunc),l.setTest(D.depthTest),l.setMask(D.depthWrite),a.setMask(D.colorWrite);const ot=D.stencilWrite;c.setTest(ot),ot&&(c.setMask(D.stencilWriteMask),c.setFunc(D.stencilFunc,D.stencilRef,D.stencilFuncMask),c.setOp(D.stencilFail,D.stencilZFail,D.stencilZPass)),T(D.polygonOffset,D.polygonOffsetFactor,D.polygonOffsetUnits),D.alphaToCoverage===!0?vt(i.SAMPLE_ALPHA_TO_COVERAGE):Gt(i.SAMPLE_ALPHA_TO_COVERAGE)}function dt(D){Z!==D&&(D?i.frontFace(i.CW):i.frontFace(i.CCW),Z=D)}function xt(D){D!==Cl?(vt(i.CULL_FACE),D!==K&&(D===Hs?i.cullFace(i.BACK):D===Pl?i.cullFace(i.FRONT):i.cullFace(i.FRONT_AND_BACK))):Gt(i.CULL_FACE),K=D}function Vt(D){D!==L&&(X&&i.lineWidth(D),L=D)}function T(D,ut,F){D?(vt(i.POLYGON_OFFSET_FILL),(k!==ut||z!==F)&&(i.polygonOffset(ut,F),k=ut,z=F)):Gt(i.POLYGON_OFFSET_FILL)}function x(D){D?vt(i.SCISSOR_TEST):Gt(i.SCISSOR_TEST)}function H(D){D===void 0&&(D=i.TEXTURE0+J-1),et!==D&&(i.activeTexture(D),et=D)}function W(D,ut,F){F===void 0&&(et===null?F=i.TEXTURE0+J-1:F=et);let ot=gt[F];ot===void 0&&(ot={type:void 0,texture:void 0},gt[F]=ot),(ot.type!==D||ot.texture!==ut)&&(et!==F&&(i.activeTexture(F),et=F),i.bindTexture(D,ut||Mt[D]),ot.type=D,ot.texture=ut)}function tt(){const D=gt[et];D!==void 0&&D.type!==void 0&&(i.bindTexture(D.type,null),D.type=void 0,D.texture=void 0)}function j(){try{i.compressedTexImage2D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function Lt(){try{i.compressedTexImage3D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function wt(){try{i.texSubImage2D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function lt(){try{i.texSubImage3D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function ht(){try{i.compressedTexSubImage2D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function Dt(){try{i.compressedTexSubImage3D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function st(){try{i.texStorage2D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function re(){try{i.texStorage3D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function kt(){try{i.texImage2D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function bt(){try{i.texImage3D.apply(i,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function St(D){Q.equals(D)===!1&&(i.scissor(D.x,D.y,D.z,D.w),Q.copy(D))}function yt(D){pt.equals(D)===!1&&(i.viewport(D.x,D.y,D.z,D.w),pt.copy(D))}function Xt(D,ut){let F=u.get(ut);F===void 0&&(F=new WeakMap,u.set(ut,F));let ot=F.get(D);ot===void 0&&(ot=i.getUniformBlockIndex(ut,D.name),F.set(D,ot))}function It(D,ut){const ot=u.get(ut).get(D);h.get(ut)!==ot&&(i.uniformBlockBinding(ut,ot,D.__bindingPointIndex),h.set(ut,ot))}function jt(){i.disable(i.BLEND),i.disable(i.CULL_FACE),i.disable(i.DEPTH_TEST),i.disable(i.POLYGON_OFFSET_FILL),i.disable(i.SCISSOR_TEST),i.disable(i.STENCIL_TEST),i.disable(i.SAMPLE_ALPHA_TO_COVERAGE),i.blendEquation(i.FUNC_ADD),i.blendFunc(i.ONE,i.ZERO),i.blendFuncSeparate(i.ONE,i.ZERO,i.ONE,i.ZERO),i.blendColor(0,0,0,0),i.colorMask(!0,!0,!0,!0),i.clearColor(0,0,0,0),i.depthMask(!0),i.depthFunc(i.LESS),i.clearDepth(1),i.stencilMask(4294967295),i.stencilFunc(i.ALWAYS,0,4294967295),i.stencilOp(i.KEEP,i.KEEP,i.KEEP),i.clearStencil(0),i.cullFace(i.BACK),i.frontFace(i.CCW),i.polygonOffset(0,0),i.activeTexture(i.TEXTURE0),i.bindFramebuffer(i.FRAMEBUFFER,null),n===!0&&(i.bindFramebuffer(i.DRAW_FRAMEBUFFER,null),i.bindFramebuffer(i.READ_FRAMEBUFFER,null)),i.useProgram(null),i.lineWidth(1),i.scissor(0,0,i.canvas.width,i.canvas.height),i.viewport(0,0,i.canvas.width,i.canvas.height),d={},et=null,gt={},m={},_=new WeakMap,M=[],p=null,f=!1,y=null,g=null,E=null,P=null,w=null,b=null,U=null,V=new zt(0,0,0),v=0,A=!1,Z=null,K=null,L=null,k=null,z=null,Q.set(0,0,i.canvas.width,i.canvas.height),pt.set(0,0,i.canvas.width,i.canvas.height),a.reset(),l.reset(),c.reset()}return{buffers:{color:a,depth:l,stencil:c},enable:vt,disable:Gt,bindFramebuffer:At,drawBuffers:R,useProgram:at,setBlending:$,setMaterial:_t,setFlipSided:dt,setCullFace:xt,setLineWidth:Vt,setPolygonOffset:T,setScissorTest:x,activeTexture:H,bindTexture:W,unbindTexture:tt,compressedTexImage2D:j,compressedTexImage3D:Lt,texImage2D:kt,texImage3D:bt,updateUBOMapping:Xt,uniformBlockBinding:It,texStorage2D:st,texStorage3D:re,texSubImage2D:wt,texSubImage3D:lt,compressedTexSubImage2D:ht,compressedTexSubImage3D:Dt,scissor:St,viewport:yt,reset:jt}}function kp(i,t,e,n,r,s,o){const a=r.isWebGL2,l=t.has("WEBGL_multisampled_render_to_texture")?t.get("WEBGL_multisampled_render_to_texture"):null,c=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),h=new it,u=new WeakMap;let d;const m=new WeakMap;let _=!1;try{_=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function M(T,x){return _?new OffscreenCanvas(T,x):pr("canvas")}function p(T,x,H,W){let tt=1;const j=Vt(T);if((j.width>W||j.height>W)&&(tt=W/Math.max(j.width,j.height)),tt<1||x===!0)if(typeof HTMLImageElement<"u"&&T instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&T instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&T instanceof ImageBitmap||typeof VideoFrame<"u"&&T instanceof VideoFrame){const Lt=x?dr:Math.floor,wt=Lt(tt*j.width),lt=Lt(tt*j.height);d===void 0&&(d=M(wt,lt));const ht=H?M(wt,lt):d;return ht.width=wt,ht.height=lt,ht.getContext("2d").drawImage(T,0,0,wt,lt),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+j.width+"x"+j.height+") to ("+wt+"x"+lt+")."),ht}else return"data"in T&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+j.width+"x"+j.height+")."),T;return T}function f(T){const x=Vt(T);return _s(x.width)&&_s(x.height)}function y(T){return a?!1:T.wrapS!==Ne||T.wrapT!==Ne||T.minFilter!==de&&T.minFilter!==ye}function g(T,x){return T.generateMipmaps&&x&&T.minFilter!==de&&T.minFilter!==ye}function E(T){i.generateMipmap(T)}function P(T,x,H,W,tt=!1){if(a===!1)return x;if(T!==null){if(i[T]!==void 0)return i[T];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+T+"'")}let j=x;if(x===i.RED&&(H===i.FLOAT&&(j=i.R32F),H===i.HALF_FLOAT&&(j=i.R16F),H===i.UNSIGNED_BYTE&&(j=i.R8)),x===i.RED_INTEGER&&(H===i.UNSIGNED_BYTE&&(j=i.R8UI),H===i.UNSIGNED_SHORT&&(j=i.R16UI),H===i.UNSIGNED_INT&&(j=i.R32UI),H===i.BYTE&&(j=i.R8I),H===i.SHORT&&(j=i.R16I),H===i.INT&&(j=i.R32I)),x===i.RG&&(H===i.FLOAT&&(j=i.RG32F),H===i.HALF_FLOAT&&(j=i.RG16F),H===i.UNSIGNED_BYTE&&(j=i.RG8)),x===i.RG_INTEGER&&(H===i.UNSIGNED_BYTE&&(j=i.RG8UI),H===i.UNSIGNED_SHORT&&(j=i.RG16UI),H===i.UNSIGNED_INT&&(j=i.RG32UI),H===i.BYTE&&(j=i.RG8I),H===i.SHORT&&(j=i.RG16I),H===i.INT&&(j=i.RG32I)),x===i.RGBA){const Lt=tt?cr:Yt.getTransfer(W);H===i.FLOAT&&(j=i.RGBA32F),H===i.HALF_FLOAT&&(j=i.RGBA16F),H===i.UNSIGNED_BYTE&&(j=Lt===$t?i.SRGB8_ALPHA8:i.RGBA8),H===i.UNSIGNED_SHORT_4_4_4_4&&(j=i.RGBA4),H===i.UNSIGNED_SHORT_5_5_5_1&&(j=i.RGB5_A1)}return(j===i.R16F||j===i.R32F||j===i.RG16F||j===i.RG32F||j===i.RGBA16F||j===i.RGBA32F)&&t.get("EXT_color_buffer_float"),j}function w(T,x,H){return g(T,H)===!0||T.isFramebufferTexture&&T.minFilter!==de&&T.minFilter!==ye?Math.log2(Math.max(x.width,x.height))+1:T.mipmaps!==void 0&&T.mipmaps.length>0?T.mipmaps.length:T.isCompressedTexture&&Array.isArray(T.image)?x.mipmaps.length:1}function b(T){return T===de||T===Ys||T===di?i.NEAREST:i.LINEAR}function U(T){const x=T.target;x.removeEventListener("dispose",U),v(x),x.isVideoTexture&&u.delete(x)}function V(T){const x=T.target;x.removeEventListener("dispose",V),Z(x)}function v(T){const x=n.get(T);if(x.__webglInit===void 0)return;const H=T.source,W=m.get(H);if(W){const tt=W[x.__cacheKey];tt.usedTimes--,tt.usedTimes===0&&A(T),Object.keys(W).length===0&&m.delete(H)}n.remove(T)}function A(T){const x=n.get(T);i.deleteTexture(x.__webglTexture);const H=T.source,W=m.get(H);delete W[x.__cacheKey],o.memory.textures--}function Z(T){const x=n.get(T);if(T.depthTexture&&T.depthTexture.dispose(),T.isWebGLCubeRenderTarget)for(let W=0;W<6;W++){if(Array.isArray(x.__webglFramebuffer[W]))for(let tt=0;tt<x.__webglFramebuffer[W].length;tt++)i.deleteFramebuffer(x.__webglFramebuffer[W][tt]);else i.deleteFramebuffer(x.__webglFramebuffer[W]);x.__webglDepthbuffer&&i.deleteRenderbuffer(x.__webglDepthbuffer[W])}else{if(Array.isArray(x.__webglFramebuffer))for(let W=0;W<x.__webglFramebuffer.length;W++)i.deleteFramebuffer(x.__webglFramebuffer[W]);else i.deleteFramebuffer(x.__webglFramebuffer);if(x.__webglDepthbuffer&&i.deleteRenderbuffer(x.__webglDepthbuffer),x.__webglMultisampledFramebuffer&&i.deleteFramebuffer(x.__webglMultisampledFramebuffer),x.__webglColorRenderbuffer)for(let W=0;W<x.__webglColorRenderbuffer.length;W++)x.__webglColorRenderbuffer[W]&&i.deleteRenderbuffer(x.__webglColorRenderbuffer[W]);x.__webglDepthRenderbuffer&&i.deleteRenderbuffer(x.__webglDepthRenderbuffer)}const H=T.textures;for(let W=0,tt=H.length;W<tt;W++){const j=n.get(H[W]);j.__webglTexture&&(i.deleteTexture(j.__webglTexture),o.memory.textures--),n.remove(H[W])}n.remove(T)}let K=0;function L(){K=0}function k(){const T=K;return T>=r.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+T+" texture units while this GPU supports only "+r.maxTextures),K+=1,T}function z(T){const x=[];return x.push(T.wrapS),x.push(T.wrapT),x.push(T.wrapR||0),x.push(T.magFilter),x.push(T.minFilter),x.push(T.anisotropy),x.push(T.internalFormat),x.push(T.format),x.push(T.type),x.push(T.generateMipmaps),x.push(T.premultiplyAlpha),x.push(T.flipY),x.push(T.unpackAlignment),x.push(T.colorSpace),x.join()}function J(T,x){const H=n.get(T);if(T.isVideoTexture&&dt(T),T.isRenderTargetTexture===!1&&T.version>0&&H.__version!==T.version){const W=T.image;if(W===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(W.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{pt(H,T,x);return}}e.bindTexture(i.TEXTURE_2D,H.__webglTexture,i.TEXTURE0+x)}function X(T,x){const H=n.get(T);if(T.version>0&&H.__version!==T.version){pt(H,T,x);return}e.bindTexture(i.TEXTURE_2D_ARRAY,H.__webglTexture,i.TEXTURE0+x)}function q(T,x){const H=n.get(T);if(T.version>0&&H.__version!==T.version){pt(H,T,x);return}e.bindTexture(i.TEXTURE_3D,H.__webglTexture,i.TEXTURE0+x)}function nt(T,x){const H=n.get(T);if(T.version>0&&H.__version!==T.version){Tt(H,T,x);return}e.bindTexture(i.TEXTURE_CUBE_MAP,H.__webglTexture,i.TEXTURE0+x)}const et={[ps]:i.REPEAT,[Ne]:i.CLAMP_TO_EDGE,[ms]:i.MIRRORED_REPEAT},gt={[de]:i.NEAREST,[Ys]:i.NEAREST_MIPMAP_NEAREST,[di]:i.NEAREST_MIPMAP_LINEAR,[ye]:i.LINEAR,[wr]:i.LINEAR_MIPMAP_NEAREST,[Rn]:i.LINEAR_MIPMAP_LINEAR},Pt={[Mc]:i.NEVER,[bc]:i.ALWAYS,[Sc]:i.LESS,[Ho]:i.LEQUAL,[yc]:i.EQUAL,[Ac]:i.GEQUAL,[Ec]:i.GREATER,[Tc]:i.NOTEQUAL};function G(T,x,H){if(x.type===He&&t.has("OES_texture_float_linear")===!1&&(x.magFilter===ye||x.magFilter===wr||x.magFilter===di||x.magFilter===Rn||x.minFilter===ye||x.minFilter===wr||x.minFilter===di||x.minFilter===Rn)&&console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),H?(i.texParameteri(T,i.TEXTURE_WRAP_S,et[x.wrapS]),i.texParameteri(T,i.TEXTURE_WRAP_T,et[x.wrapT]),(T===i.TEXTURE_3D||T===i.TEXTURE_2D_ARRAY)&&i.texParameteri(T,i.TEXTURE_WRAP_R,et[x.wrapR]),i.texParameteri(T,i.TEXTURE_MAG_FILTER,gt[x.magFilter]),i.texParameteri(T,i.TEXTURE_MIN_FILTER,gt[x.minFilter])):(i.texParameteri(T,i.TEXTURE_WRAP_S,i.CLAMP_TO_EDGE),i.texParameteri(T,i.TEXTURE_WRAP_T,i.CLAMP_TO_EDGE),(T===i.TEXTURE_3D||T===i.TEXTURE_2D_ARRAY)&&i.texParameteri(T,i.TEXTURE_WRAP_R,i.CLAMP_TO_EDGE),(x.wrapS!==Ne||x.wrapT!==Ne)&&console.warn("THREE.WebGLRenderer: Texture is not power of two. Texture.wrapS and Texture.wrapT should be set to THREE.ClampToEdgeWrapping."),i.texParameteri(T,i.TEXTURE_MAG_FILTER,b(x.magFilter)),i.texParameteri(T,i.TEXTURE_MIN_FILTER,b(x.minFilter)),x.minFilter!==de&&x.minFilter!==ye&&console.warn("THREE.WebGLRenderer: Texture is not power of two. Texture.minFilter should be set to THREE.NearestFilter or THREE.LinearFilter.")),x.compareFunction&&(i.texParameteri(T,i.TEXTURE_COMPARE_MODE,i.COMPARE_REF_TO_TEXTURE),i.texParameteri(T,i.TEXTURE_COMPARE_FUNC,Pt[x.compareFunction])),t.has("EXT_texture_filter_anisotropic")===!0){if(x.magFilter===de||x.minFilter!==di&&x.minFilter!==Rn||x.type===He&&t.has("OES_texture_float_linear")===!1||a===!1&&x.type===Ai&&t.has("OES_texture_half_float_linear")===!1)return;if(x.anisotropy>1||n.get(x).__currentAnisotropy){const W=t.get("EXT_texture_filter_anisotropic");i.texParameterf(T,W.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(x.anisotropy,r.getMaxAnisotropy())),n.get(x).__currentAnisotropy=x.anisotropy}}}function Q(T,x){let H=!1;T.__webglInit===void 0&&(T.__webglInit=!0,x.addEventListener("dispose",U));const W=x.source;let tt=m.get(W);tt===void 0&&(tt={},m.set(W,tt));const j=z(x);if(j!==T.__cacheKey){tt[j]===void 0&&(tt[j]={texture:i.createTexture(),usedTimes:0},o.memory.textures++,H=!0),tt[j].usedTimes++;const Lt=tt[T.__cacheKey];Lt!==void 0&&(tt[T.__cacheKey].usedTimes--,Lt.usedTimes===0&&A(x)),T.__cacheKey=j,T.__webglTexture=tt[j].texture}return H}function pt(T,x,H){let W=i.TEXTURE_2D;(x.isDataArrayTexture||x.isCompressedArrayTexture)&&(W=i.TEXTURE_2D_ARRAY),x.isData3DTexture&&(W=i.TEXTURE_3D);const tt=Q(T,x),j=x.source;e.bindTexture(W,T.__webglTexture,i.TEXTURE0+H);const Lt=n.get(j);if(j.version!==Lt.__version||tt===!0){e.activeTexture(i.TEXTURE0+H);const wt=Yt.getPrimaries(Yt.workingColorSpace),lt=x.colorSpace===ln?null:Yt.getPrimaries(x.colorSpace),ht=x.colorSpace===ln||wt===lt?i.NONE:i.BROWSER_DEFAULT_WEBGL;i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL,x.flipY),i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL,x.premultiplyAlpha),i.pixelStorei(i.UNPACK_ALIGNMENT,x.unpackAlignment),i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL,ht);const Dt=y(x)&&f(x.image)===!1;let st=p(x.image,Dt,!1,r.maxTextureSize);st=xt(x,st);const re=f(st)||a,kt=s.convert(x.format,x.colorSpace);let bt=s.convert(x.type),St=P(x.internalFormat,kt,bt,x.colorSpace,x.isVideoTexture);G(W,x,re);let yt;const Xt=x.mipmaps,It=a&&x.isVideoTexture!==!0&&St!==zo,jt=Lt.__version===void 0||tt===!0,D=j.dataReady,ut=w(x,st,re);if(x.isDepthTexture)St=i.DEPTH_COMPONENT,a?x.type===He?St=i.DEPTH_COMPONENT32F:x.type===cn?St=i.DEPTH_COMPONENT24:x.type===Cn?St=i.DEPTH24_STENCIL8:St=i.DEPTH_COMPONENT16:x.type===He&&console.error("WebGLRenderer: Floating point depth texture requires WebGL2."),x.format===Pn&&St===i.DEPTH_COMPONENT&&x.type!==Ts&&x.type!==cn&&(console.warn("THREE.WebGLRenderer: Use UnsignedShortType or UnsignedIntType for DepthFormat DepthTexture."),x.type=cn,bt=s.convert(x.type)),x.format===ai&&St===i.DEPTH_COMPONENT&&(St=i.DEPTH_STENCIL,x.type!==Cn&&(console.warn("THREE.WebGLRenderer: Use UnsignedInt248Type for DepthStencilFormat DepthTexture."),x.type=Cn,bt=s.convert(x.type))),jt&&(It?e.texStorage2D(i.TEXTURE_2D,1,St,st.width,st.height):e.texImage2D(i.TEXTURE_2D,0,St,st.width,st.height,0,kt,bt,null));else if(x.isDataTexture)if(Xt.length>0&&re){It&&jt&&e.texStorage2D(i.TEXTURE_2D,ut,St,Xt[0].width,Xt[0].height);for(let F=0,ot=Xt.length;F<ot;F++)yt=Xt[F],It?D&&e.texSubImage2D(i.TEXTURE_2D,F,0,0,yt.width,yt.height,kt,bt,yt.data):e.texImage2D(i.TEXTURE_2D,F,St,yt.width,yt.height,0,kt,bt,yt.data);x.generateMipmaps=!1}else It?(jt&&e.texStorage2D(i.TEXTURE_2D,ut,St,st.width,st.height),D&&e.texSubImage2D(i.TEXTURE_2D,0,0,0,st.width,st.height,kt,bt,st.data)):e.texImage2D(i.TEXTURE_2D,0,St,st.width,st.height,0,kt,bt,st.data);else if(x.isCompressedTexture)if(x.isCompressedArrayTexture){It&&jt&&e.texStorage3D(i.TEXTURE_2D_ARRAY,ut,St,Xt[0].width,Xt[0].height,st.depth);for(let F=0,ot=Xt.length;F<ot;F++)yt=Xt[F],x.format!==Fe?kt!==null?It?D&&e.compressedTexSubImage3D(i.TEXTURE_2D_ARRAY,F,0,0,0,yt.width,yt.height,st.depth,kt,yt.data,0,0):e.compressedTexImage3D(i.TEXTURE_2D_ARRAY,F,St,yt.width,yt.height,st.depth,0,yt.data,0,0):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):It?D&&e.texSubImage3D(i.TEXTURE_2D_ARRAY,F,0,0,0,yt.width,yt.height,st.depth,kt,bt,yt.data):e.texImage3D(i.TEXTURE_2D_ARRAY,F,St,yt.width,yt.height,st.depth,0,kt,bt,yt.data)}else{It&&jt&&e.texStorage2D(i.TEXTURE_2D,ut,St,Xt[0].width,Xt[0].height);for(let F=0,ot=Xt.length;F<ot;F++)yt=Xt[F],x.format!==Fe?kt!==null?It?D&&e.compressedTexSubImage2D(i.TEXTURE_2D,F,0,0,yt.width,yt.height,kt,yt.data):e.compressedTexImage2D(i.TEXTURE_2D,F,St,yt.width,yt.height,0,yt.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):It?D&&e.texSubImage2D(i.TEXTURE_2D,F,0,0,yt.width,yt.height,kt,bt,yt.data):e.texImage2D(i.TEXTURE_2D,F,St,yt.width,yt.height,0,kt,bt,yt.data)}else if(x.isDataArrayTexture)It?(jt&&e.texStorage3D(i.TEXTURE_2D_ARRAY,ut,St,st.width,st.height,st.depth),D&&e.texSubImage3D(i.TEXTURE_2D_ARRAY,0,0,0,0,st.width,st.height,st.depth,kt,bt,st.data)):e.texImage3D(i.TEXTURE_2D_ARRAY,0,St,st.width,st.height,st.depth,0,kt,bt,st.data);else if(x.isData3DTexture)It?(jt&&e.texStorage3D(i.TEXTURE_3D,ut,St,st.width,st.height,st.depth),D&&e.texSubImage3D(i.TEXTURE_3D,0,0,0,0,st.width,st.height,st.depth,kt,bt,st.data)):e.texImage3D(i.TEXTURE_3D,0,St,st.width,st.height,st.depth,0,kt,bt,st.data);else if(x.isFramebufferTexture){if(jt)if(It)e.texStorage2D(i.TEXTURE_2D,ut,St,st.width,st.height);else{let F=st.width,ot=st.height;for(let ft=0;ft<ut;ft++)e.texImage2D(i.TEXTURE_2D,ft,St,F,ot,0,kt,bt,null),F>>=1,ot>>=1}}else if(Xt.length>0&&re){if(It&&jt){const F=Vt(Xt[0]);e.texStorage2D(i.TEXTURE_2D,ut,St,F.width,F.height)}for(let F=0,ot=Xt.length;F<ot;F++)yt=Xt[F],It?D&&e.texSubImage2D(i.TEXTURE_2D,F,0,0,kt,bt,yt):e.texImage2D(i.TEXTURE_2D,F,St,kt,bt,yt);x.generateMipmaps=!1}else if(It){if(jt){const F=Vt(st);e.texStorage2D(i.TEXTURE_2D,ut,St,F.width,F.height)}D&&e.texSubImage2D(i.TEXTURE_2D,0,0,0,kt,bt,st)}else e.texImage2D(i.TEXTURE_2D,0,St,kt,bt,st);g(x,re)&&E(W),Lt.__version=j.version,x.onUpdate&&x.onUpdate(x)}T.__version=x.version}function Tt(T,x,H){if(x.image.length!==6)return;const W=Q(T,x),tt=x.source;e.bindTexture(i.TEXTURE_CUBE_MAP,T.__webglTexture,i.TEXTURE0+H);const j=n.get(tt);if(tt.version!==j.__version||W===!0){e.activeTexture(i.TEXTURE0+H);const Lt=Yt.getPrimaries(Yt.workingColorSpace),wt=x.colorSpace===ln?null:Yt.getPrimaries(x.colorSpace),lt=x.colorSpace===ln||Lt===wt?i.NONE:i.BROWSER_DEFAULT_WEBGL;i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL,x.flipY),i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL,x.premultiplyAlpha),i.pixelStorei(i.UNPACK_ALIGNMENT,x.unpackAlignment),i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL,lt);const ht=x.isCompressedTexture||x.image[0].isCompressedTexture,Dt=x.image[0]&&x.image[0].isDataTexture,st=[];for(let F=0;F<6;F++)!ht&&!Dt?st[F]=p(x.image[F],!1,!0,r.maxCubemapSize):st[F]=Dt?x.image[F].image:x.image[F],st[F]=xt(x,st[F]);const re=st[0],kt=f(re)||a,bt=s.convert(x.format,x.colorSpace),St=s.convert(x.type),yt=P(x.internalFormat,bt,St,x.colorSpace),Xt=a&&x.isVideoTexture!==!0,It=j.__version===void 0||W===!0,jt=tt.dataReady;let D=w(x,re,kt);G(i.TEXTURE_CUBE_MAP,x,kt);let ut;if(ht){Xt&&It&&e.texStorage2D(i.TEXTURE_CUBE_MAP,D,yt,re.width,re.height);for(let F=0;F<6;F++){ut=st[F].mipmaps;for(let ot=0;ot<ut.length;ot++){const ft=ut[ot];x.format!==Fe?bt!==null?Xt?jt&&e.compressedTexSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,ot,0,0,ft.width,ft.height,bt,ft.data):e.compressedTexImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,ot,yt,ft.width,ft.height,0,ft.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):Xt?jt&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,ot,0,0,ft.width,ft.height,bt,St,ft.data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,ot,yt,ft.width,ft.height,0,bt,St,ft.data)}}}else{if(ut=x.mipmaps,Xt&&It){ut.length>0&&D++;const F=Vt(st[0]);e.texStorage2D(i.TEXTURE_CUBE_MAP,D,yt,F.width,F.height)}for(let F=0;F<6;F++)if(Dt){Xt?jt&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,0,0,0,st[F].width,st[F].height,bt,St,st[F].data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,0,yt,st[F].width,st[F].height,0,bt,St,st[F].data);for(let ot=0;ot<ut.length;ot++){const Wt=ut[ot].image[F].image;Xt?jt&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,ot+1,0,0,Wt.width,Wt.height,bt,St,Wt.data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,ot+1,yt,Wt.width,Wt.height,0,bt,St,Wt.data)}}else{Xt?jt&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,0,0,0,bt,St,st[F]):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,0,yt,bt,St,st[F]);for(let ot=0;ot<ut.length;ot++){const ft=ut[ot];Xt?jt&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,ot+1,0,0,bt,St,ft.image[F]):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+F,ot+1,yt,bt,St,ft.image[F])}}}g(x,kt)&&E(i.TEXTURE_CUBE_MAP),j.__version=tt.version,x.onUpdate&&x.onUpdate(x)}T.__version=x.version}function Mt(T,x,H,W,tt,j){const Lt=s.convert(H.format,H.colorSpace),wt=s.convert(H.type),lt=P(H.internalFormat,Lt,wt,H.colorSpace);if(!n.get(x).__hasExternalTextures){const Dt=Math.max(1,x.width>>j),st=Math.max(1,x.height>>j);tt===i.TEXTURE_3D||tt===i.TEXTURE_2D_ARRAY?e.texImage3D(tt,j,lt,Dt,st,x.depth,0,Lt,wt,null):e.texImage2D(tt,j,lt,Dt,st,0,Lt,wt,null)}e.bindFramebuffer(i.FRAMEBUFFER,T),_t(x)?l.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,W,tt,n.get(H).__webglTexture,0,$(x)):(tt===i.TEXTURE_2D||tt>=i.TEXTURE_CUBE_MAP_POSITIVE_X&&tt<=i.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&i.framebufferTexture2D(i.FRAMEBUFFER,W,tt,n.get(H).__webglTexture,j),e.bindFramebuffer(i.FRAMEBUFFER,null)}function vt(T,x,H){if(i.bindRenderbuffer(i.RENDERBUFFER,T),x.depthBuffer&&!x.stencilBuffer){let W=a===!0?i.DEPTH_COMPONENT24:i.DEPTH_COMPONENT16;if(H||_t(x)){const tt=x.depthTexture;tt&&tt.isDepthTexture&&(tt.type===He?W=i.DEPTH_COMPONENT32F:tt.type===cn&&(W=i.DEPTH_COMPONENT24));const j=$(x);_t(x)?l.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,j,W,x.width,x.height):i.renderbufferStorageMultisample(i.RENDERBUFFER,j,W,x.width,x.height)}else i.renderbufferStorage(i.RENDERBUFFER,W,x.width,x.height);i.framebufferRenderbuffer(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.RENDERBUFFER,T)}else if(x.depthBuffer&&x.stencilBuffer){const W=$(x);H&&_t(x)===!1?i.renderbufferStorageMultisample(i.RENDERBUFFER,W,i.DEPTH24_STENCIL8,x.width,x.height):_t(x)?l.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,W,i.DEPTH24_STENCIL8,x.width,x.height):i.renderbufferStorage(i.RENDERBUFFER,i.DEPTH_STENCIL,x.width,x.height),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.RENDERBUFFER,T)}else{const W=x.textures;for(let tt=0;tt<W.length;tt++){const j=W[tt],Lt=s.convert(j.format,j.colorSpace),wt=s.convert(j.type),lt=P(j.internalFormat,Lt,wt,j.colorSpace),ht=$(x);H&&_t(x)===!1?i.renderbufferStorageMultisample(i.RENDERBUFFER,ht,lt,x.width,x.height):_t(x)?l.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,ht,lt,x.width,x.height):i.renderbufferStorage(i.RENDERBUFFER,lt,x.width,x.height)}}i.bindRenderbuffer(i.RENDERBUFFER,null)}function Gt(T,x){if(x&&x.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(e.bindFramebuffer(i.FRAMEBUFFER,T),!(x.depthTexture&&x.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");(!n.get(x.depthTexture).__webglTexture||x.depthTexture.image.width!==x.width||x.depthTexture.image.height!==x.height)&&(x.depthTexture.image.width=x.width,x.depthTexture.image.height=x.height,x.depthTexture.needsUpdate=!0),J(x.depthTexture,0);const W=n.get(x.depthTexture).__webglTexture,tt=$(x);if(x.depthTexture.format===Pn)_t(x)?l.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.TEXTURE_2D,W,0,tt):i.framebufferTexture2D(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.TEXTURE_2D,W,0);else if(x.depthTexture.format===ai)_t(x)?l.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.TEXTURE_2D,W,0,tt):i.framebufferTexture2D(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.TEXTURE_2D,W,0);else throw new Error("Unknown depthTexture format")}function At(T){const x=n.get(T),H=T.isWebGLCubeRenderTarget===!0;if(T.depthTexture&&!x.__autoAllocateDepthBuffer){if(H)throw new Error("target.depthTexture not supported in Cube render targets");Gt(x.__webglFramebuffer,T)}else if(H){x.__webglDepthbuffer=[];for(let W=0;W<6;W++)e.bindFramebuffer(i.FRAMEBUFFER,x.__webglFramebuffer[W]),x.__webglDepthbuffer[W]=i.createRenderbuffer(),vt(x.__webglDepthbuffer[W],T,!1)}else e.bindFramebuffer(i.FRAMEBUFFER,x.__webglFramebuffer),x.__webglDepthbuffer=i.createRenderbuffer(),vt(x.__webglDepthbuffer,T,!1);e.bindFramebuffer(i.FRAMEBUFFER,null)}function R(T,x,H){const W=n.get(T);x!==void 0&&Mt(W.__webglFramebuffer,T,T.texture,i.COLOR_ATTACHMENT0,i.TEXTURE_2D,0),H!==void 0&&At(T)}function at(T){const x=T.texture,H=n.get(T),W=n.get(x);T.addEventListener("dispose",V);const tt=T.textures,j=T.isWebGLCubeRenderTarget===!0,Lt=tt.length>1,wt=f(T)||a;if(Lt||(W.__webglTexture===void 0&&(W.__webglTexture=i.createTexture()),W.__version=x.version,o.memory.textures++),j){H.__webglFramebuffer=[];for(let lt=0;lt<6;lt++)if(a&&x.mipmaps&&x.mipmaps.length>0){H.__webglFramebuffer[lt]=[];for(let ht=0;ht<x.mipmaps.length;ht++)H.__webglFramebuffer[lt][ht]=i.createFramebuffer()}else H.__webglFramebuffer[lt]=i.createFramebuffer()}else{if(a&&x.mipmaps&&x.mipmaps.length>0){H.__webglFramebuffer=[];for(let lt=0;lt<x.mipmaps.length;lt++)H.__webglFramebuffer[lt]=i.createFramebuffer()}else H.__webglFramebuffer=i.createFramebuffer();if(Lt)if(r.drawBuffers)for(let lt=0,ht=tt.length;lt<ht;lt++){const Dt=n.get(tt[lt]);Dt.__webglTexture===void 0&&(Dt.__webglTexture=i.createTexture(),o.memory.textures++)}else console.warn("THREE.WebGLRenderer: WebGLMultipleRenderTargets can only be used with WebGL2 or WEBGL_draw_buffers extension.");if(a&&T.samples>0&&_t(T)===!1){H.__webglMultisampledFramebuffer=i.createFramebuffer(),H.__webglColorRenderbuffer=[],e.bindFramebuffer(i.FRAMEBUFFER,H.__webglMultisampledFramebuffer);for(let lt=0;lt<tt.length;lt++){const ht=tt[lt];H.__webglColorRenderbuffer[lt]=i.createRenderbuffer(),i.bindRenderbuffer(i.RENDERBUFFER,H.__webglColorRenderbuffer[lt]);const Dt=s.convert(ht.format,ht.colorSpace),st=s.convert(ht.type),re=P(ht.internalFormat,Dt,st,ht.colorSpace,T.isXRRenderTarget===!0),kt=$(T);i.renderbufferStorageMultisample(i.RENDERBUFFER,kt,re,T.width,T.height),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+lt,i.RENDERBUFFER,H.__webglColorRenderbuffer[lt])}i.bindRenderbuffer(i.RENDERBUFFER,null),T.depthBuffer&&(H.__webglDepthRenderbuffer=i.createRenderbuffer(),vt(H.__webglDepthRenderbuffer,T,!0)),e.bindFramebuffer(i.FRAMEBUFFER,null)}}if(j){e.bindTexture(i.TEXTURE_CUBE_MAP,W.__webglTexture),G(i.TEXTURE_CUBE_MAP,x,wt);for(let lt=0;lt<6;lt++)if(a&&x.mipmaps&&x.mipmaps.length>0)for(let ht=0;ht<x.mipmaps.length;ht++)Mt(H.__webglFramebuffer[lt][ht],T,x,i.COLOR_ATTACHMENT0,i.TEXTURE_CUBE_MAP_POSITIVE_X+lt,ht);else Mt(H.__webglFramebuffer[lt],T,x,i.COLOR_ATTACHMENT0,i.TEXTURE_CUBE_MAP_POSITIVE_X+lt,0);g(x,wt)&&E(i.TEXTURE_CUBE_MAP),e.unbindTexture()}else if(Lt){for(let lt=0,ht=tt.length;lt<ht;lt++){const Dt=tt[lt],st=n.get(Dt);e.bindTexture(i.TEXTURE_2D,st.__webglTexture),G(i.TEXTURE_2D,Dt,wt),Mt(H.__webglFramebuffer,T,Dt,i.COLOR_ATTACHMENT0+lt,i.TEXTURE_2D,0),g(Dt,wt)&&E(i.TEXTURE_2D)}e.unbindTexture()}else{let lt=i.TEXTURE_2D;if((T.isWebGL3DRenderTarget||T.isWebGLArrayRenderTarget)&&(a?lt=T.isWebGL3DRenderTarget?i.TEXTURE_3D:i.TEXTURE_2D_ARRAY:console.error("THREE.WebGLTextures: THREE.Data3DTexture and THREE.DataArrayTexture only supported with WebGL2.")),e.bindTexture(lt,W.__webglTexture),G(lt,x,wt),a&&x.mipmaps&&x.mipmaps.length>0)for(let ht=0;ht<x.mipmaps.length;ht++)Mt(H.__webglFramebuffer[ht],T,x,i.COLOR_ATTACHMENT0,lt,ht);else Mt(H.__webglFramebuffer,T,x,i.COLOR_ATTACHMENT0,lt,0);g(x,wt)&&E(lt),e.unbindTexture()}T.depthBuffer&&At(T)}function Y(T){const x=f(T)||a,H=T.textures;for(let W=0,tt=H.length;W<tt;W++){const j=H[W];if(g(j,x)){const Lt=T.isWebGLCubeRenderTarget?i.TEXTURE_CUBE_MAP:i.TEXTURE_2D,wt=n.get(j).__webglTexture;e.bindTexture(Lt,wt),E(Lt),e.unbindTexture()}}}function rt(T){if(a&&T.samples>0&&_t(T)===!1){const x=T.textures,H=T.width,W=T.height;let tt=i.COLOR_BUFFER_BIT;const j=[],Lt=T.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,wt=n.get(T),lt=x.length>1;if(lt)for(let ht=0;ht<x.length;ht++)e.bindFramebuffer(i.FRAMEBUFFER,wt.__webglMultisampledFramebuffer),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+ht,i.RENDERBUFFER,null),e.bindFramebuffer(i.FRAMEBUFFER,wt.__webglFramebuffer),i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0+ht,i.TEXTURE_2D,null,0);e.bindFramebuffer(i.READ_FRAMEBUFFER,wt.__webglMultisampledFramebuffer),e.bindFramebuffer(i.DRAW_FRAMEBUFFER,wt.__webglFramebuffer);for(let ht=0;ht<x.length;ht++){j.push(i.COLOR_ATTACHMENT0+ht),T.depthBuffer&&j.push(Lt);const Dt=wt.__ignoreDepthValues!==void 0?wt.__ignoreDepthValues:!1;if(Dt===!1&&(T.depthBuffer&&(tt|=i.DEPTH_BUFFER_BIT),T.stencilBuffer&&(tt|=i.STENCIL_BUFFER_BIT)),lt&&i.framebufferRenderbuffer(i.READ_FRAMEBUFFER,i.COLOR_ATTACHMENT0,i.RENDERBUFFER,wt.__webglColorRenderbuffer[ht]),Dt===!0&&(i.invalidateFramebuffer(i.READ_FRAMEBUFFER,[Lt]),i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER,[Lt])),lt){const st=n.get(x[ht]).__webglTexture;i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0,i.TEXTURE_2D,st,0)}i.blitFramebuffer(0,0,H,W,0,0,H,W,tt,i.NEAREST),c&&i.invalidateFramebuffer(i.READ_FRAMEBUFFER,j)}if(e.bindFramebuffer(i.READ_FRAMEBUFFER,null),e.bindFramebuffer(i.DRAW_FRAMEBUFFER,null),lt)for(let ht=0;ht<x.length;ht++){e.bindFramebuffer(i.FRAMEBUFFER,wt.__webglMultisampledFramebuffer),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+ht,i.RENDERBUFFER,wt.__webglColorRenderbuffer[ht]);const Dt=n.get(x[ht]).__webglTexture;e.bindFramebuffer(i.FRAMEBUFFER,wt.__webglFramebuffer),i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0+ht,i.TEXTURE_2D,Dt,0)}e.bindFramebuffer(i.DRAW_FRAMEBUFFER,wt.__webglMultisampledFramebuffer)}}function $(T){return Math.min(r.maxSamples,T.samples)}function _t(T){const x=n.get(T);return a&&T.samples>0&&t.has("WEBGL_multisampled_render_to_texture")===!0&&x.__useRenderToTexture!==!1}function dt(T){const x=o.render.frame;u.get(T)!==x&&(u.set(T,x),T.update())}function xt(T,x){const H=T.colorSpace,W=T.format,tt=T.type;return T.isCompressedTexture===!0||T.isVideoTexture===!0||T.format===gs||H!==mn&&H!==ln&&(Yt.getTransfer(H)===$t?a===!1?t.has("EXT_sRGB")===!0&&W===Fe?(T.format=gs,T.minFilter=ye,T.generateMipmaps=!1):x=ko.sRGBToLinear(x):(W!==Fe||tt!==fn)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",H)),x}function Vt(T){return typeof HTMLImageElement<"u"&&T instanceof HTMLImageElement?(h.width=T.naturalWidth||T.width,h.height=T.naturalHeight||T.height):typeof VideoFrame<"u"&&T instanceof VideoFrame?(h.width=T.displayWidth,h.height=T.displayHeight):(h.width=T.width,h.height=T.height),h}this.allocateTextureUnit=k,this.resetTextureUnits=L,this.setTexture2D=J,this.setTexture2DArray=X,this.setTexture3D=q,this.setTextureCube=nt,this.rebindTextures=R,this.setupRenderTarget=at,this.updateRenderTargetMipmap=Y,this.updateMultisampleRenderTarget=rt,this.setupDepthRenderbuffer=At,this.setupFrameBufferTexture=Mt,this.useMultisampledRTT=_t}function Wp(i,t,e){const n=e.isWebGL2;function r(s,o=ln){let a;const l=Yt.getTransfer(o);if(s===fn)return i.UNSIGNED_BYTE;if(s===Uo)return i.UNSIGNED_SHORT_4_4_4_4;if(s===Io)return i.UNSIGNED_SHORT_5_5_5_1;if(s===hc)return i.BYTE;if(s===uc)return i.SHORT;if(s===Ts)return i.UNSIGNED_SHORT;if(s===Do)return i.INT;if(s===cn)return i.UNSIGNED_INT;if(s===He)return i.FLOAT;if(s===Ai)return n?i.HALF_FLOAT:(a=t.get("OES_texture_half_float"),a!==null?a.HALF_FLOAT_OES:null);if(s===fc)return i.ALPHA;if(s===Fe)return i.RGBA;if(s===dc)return i.LUMINANCE;if(s===pc)return i.LUMINANCE_ALPHA;if(s===Pn)return i.DEPTH_COMPONENT;if(s===ai)return i.DEPTH_STENCIL;if(s===gs)return a=t.get("EXT_sRGB"),a!==null?a.SRGB_ALPHA_EXT:null;if(s===No)return i.RED;if(s===Fo)return i.RED_INTEGER;if(s===mc)return i.RG;if(s===Oo)return i.RG_INTEGER;if(s===Bo)return i.RGBA_INTEGER;if(s===Rr||s===Cr||s===Pr||s===Lr)if(l===$t)if(a=t.get("WEBGL_compressed_texture_s3tc_srgb"),a!==null){if(s===Rr)return a.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(s===Cr)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(s===Pr)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(s===Lr)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(a=t.get("WEBGL_compressed_texture_s3tc"),a!==null){if(s===Rr)return a.COMPRESSED_RGB_S3TC_DXT1_EXT;if(s===Cr)return a.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(s===Pr)return a.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(s===Lr)return a.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(s===Js||s===Zs||s===Ks||s===$s)if(a=t.get("WEBGL_compressed_texture_pvrtc"),a!==null){if(s===Js)return a.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(s===Zs)return a.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(s===Ks)return a.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(s===$s)return a.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(s===zo)return a=t.get("WEBGL_compressed_texture_etc1"),a!==null?a.COMPRESSED_RGB_ETC1_WEBGL:null;if(s===js||s===Qs)if(a=t.get("WEBGL_compressed_texture_etc"),a!==null){if(s===js)return l===$t?a.COMPRESSED_SRGB8_ETC2:a.COMPRESSED_RGB8_ETC2;if(s===Qs)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:a.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(s===ta||s===ea||s===na||s===ia||s===ra||s===sa||s===aa||s===oa||s===la||s===ca||s===ha||s===ua||s===fa||s===da)if(a=t.get("WEBGL_compressed_texture_astc"),a!==null){if(s===ta)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:a.COMPRESSED_RGBA_ASTC_4x4_KHR;if(s===ea)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:a.COMPRESSED_RGBA_ASTC_5x4_KHR;if(s===na)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:a.COMPRESSED_RGBA_ASTC_5x5_KHR;if(s===ia)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:a.COMPRESSED_RGBA_ASTC_6x5_KHR;if(s===ra)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:a.COMPRESSED_RGBA_ASTC_6x6_KHR;if(s===sa)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:a.COMPRESSED_RGBA_ASTC_8x5_KHR;if(s===aa)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:a.COMPRESSED_RGBA_ASTC_8x6_KHR;if(s===oa)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:a.COMPRESSED_RGBA_ASTC_8x8_KHR;if(s===la)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:a.COMPRESSED_RGBA_ASTC_10x5_KHR;if(s===ca)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:a.COMPRESSED_RGBA_ASTC_10x6_KHR;if(s===ha)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:a.COMPRESSED_RGBA_ASTC_10x8_KHR;if(s===ua)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:a.COMPRESSED_RGBA_ASTC_10x10_KHR;if(s===fa)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:a.COMPRESSED_RGBA_ASTC_12x10_KHR;if(s===da)return l===$t?a.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:a.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(s===Dr||s===pa||s===ma)if(a=t.get("EXT_texture_compression_bptc"),a!==null){if(s===Dr)return l===$t?a.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:a.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(s===pa)return a.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(s===ma)return a.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(s===gc||s===ga||s===_a||s===va)if(a=t.get("EXT_texture_compression_rgtc"),a!==null){if(s===Dr)return a.COMPRESSED_RED_RGTC1_EXT;if(s===ga)return a.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(s===_a)return a.COMPRESSED_RED_GREEN_RGTC2_EXT;if(s===va)return a.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return s===Cn?n?i.UNSIGNED_INT_24_8:(a=t.get("WEBGL_depth_texture"),a!==null?a.UNSIGNED_INT_24_8_WEBGL:null):i[s]!==void 0?i[s]:null}return{convert:r}}class Xp extends Pe{constructor(t=[]){super(),this.isArrayCamera=!0,this.cameras=t}}class er extends ue{constructor(){super(),this.isGroup=!0,this.type="Group"}}const qp={type:"move"};class is{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new er,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new er,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new C,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new C),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new er,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new C,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new C),this._grip}dispatchEvent(t){return this._targetRay!==null&&this._targetRay.dispatchEvent(t),this._grip!==null&&this._grip.dispatchEvent(t),this._hand!==null&&this._hand.dispatchEvent(t),this}connect(t){if(t&&t.hand){const e=this._hand;if(e)for(const n of t.hand.values())this._getHandJoint(e,n)}return this.dispatchEvent({type:"connected",data:t}),this}disconnect(t){return this.dispatchEvent({type:"disconnected",data:t}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(t,e,n){let r=null,s=null,o=null;const a=this._targetRay,l=this._grip,c=this._hand;if(t&&e.session.visibilityState!=="visible-blurred"){if(c&&t.hand){o=!0;for(const M of t.hand.values()){const p=e.getJointPose(M,n),f=this._getHandJoint(c,M);p!==null&&(f.matrix.fromArray(p.transform.matrix),f.matrix.decompose(f.position,f.rotation,f.scale),f.matrixWorldNeedsUpdate=!0,f.jointRadius=p.radius),f.visible=p!==null}const h=c.joints["index-finger-tip"],u=c.joints["thumb-tip"],d=h.position.distanceTo(u.position),m=.02,_=.005;c.inputState.pinching&&d>m+_?(c.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:t.handedness,target:this})):!c.inputState.pinching&&d<=m-_&&(c.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:t.handedness,target:this}))}else l!==null&&t.gripSpace&&(s=e.getPose(t.gripSpace,n),s!==null&&(l.matrix.fromArray(s.transform.matrix),l.matrix.decompose(l.position,l.rotation,l.scale),l.matrixWorldNeedsUpdate=!0,s.linearVelocity?(l.hasLinearVelocity=!0,l.linearVelocity.copy(s.linearVelocity)):l.hasLinearVelocity=!1,s.angularVelocity?(l.hasAngularVelocity=!0,l.angularVelocity.copy(s.angularVelocity)):l.hasAngularVelocity=!1));a!==null&&(r=e.getPose(t.targetRaySpace,n),r===null&&s!==null&&(r=s),r!==null&&(a.matrix.fromArray(r.transform.matrix),a.matrix.decompose(a.position,a.rotation,a.scale),a.matrixWorldNeedsUpdate=!0,r.linearVelocity?(a.hasLinearVelocity=!0,a.linearVelocity.copy(r.linearVelocity)):a.hasLinearVelocity=!1,r.angularVelocity?(a.hasAngularVelocity=!0,a.angularVelocity.copy(r.angularVelocity)):a.hasAngularVelocity=!1,this.dispatchEvent(qp)))}return a!==null&&(a.visible=r!==null),l!==null&&(l.visible=s!==null),c!==null&&(c.visible=o!==null),this}_getHandJoint(t,e){if(t.joints[e.jointName]===void 0){const n=new er;n.matrixAutoUpdate=!1,n.visible=!1,t.joints[e.jointName]=n,t.add(n)}return t.joints[e.jointName]}}const Yp=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,Jp=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepthEXT = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepthEXT = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`;class Zp{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(t,e,n){if(this.texture===null){const r=new ve,s=t.properties.get(r);s.__webglTexture=e.texture,(e.depthNear!=n.depthNear||e.depthFar!=n.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=r}}render(t,e){if(this.texture!==null){if(this.mesh===null){const n=e.cameras[0].viewport,r=new tn({extensions:{fragDepth:!0},vertexShader:Yp,fragmentShader:Jp,uniforms:{depthColor:{value:this.texture},depthWidth:{value:n.z},depthHeight:{value:n.w}}});this.mesh=new Oe(new _r(20,20),r)}t.render(this.mesh,e)}}reset(){this.texture=null,this.mesh=null}}class Kp extends li{constructor(t,e){super();const n=this;let r=null,s=1,o=null,a="local-floor",l=1,c=null,h=null,u=null,d=null,m=null,_=null;const M=new Zp,p=e.getContextAttributes();let f=null,y=null;const g=[],E=[],P=new it;let w=null;const b=new Pe;b.layers.enable(1),b.viewport=new te;const U=new Pe;U.layers.enable(2),U.viewport=new te;const V=[b,U],v=new Xp;v.layers.enable(1),v.layers.enable(2);let A=null,Z=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(G){let Q=g[G];return Q===void 0&&(Q=new is,g[G]=Q),Q.getTargetRaySpace()},this.getControllerGrip=function(G){let Q=g[G];return Q===void 0&&(Q=new is,g[G]=Q),Q.getGripSpace()},this.getHand=function(G){let Q=g[G];return Q===void 0&&(Q=new is,g[G]=Q),Q.getHandSpace()};function K(G){const Q=E.indexOf(G.inputSource);if(Q===-1)return;const pt=g[Q];pt!==void 0&&(pt.update(G.inputSource,G.frame,c||o),pt.dispatchEvent({type:G.type,data:G.inputSource}))}function L(){r.removeEventListener("select",K),r.removeEventListener("selectstart",K),r.removeEventListener("selectend",K),r.removeEventListener("squeeze",K),r.removeEventListener("squeezestart",K),r.removeEventListener("squeezeend",K),r.removeEventListener("end",L),r.removeEventListener("inputsourceschange",k);for(let G=0;G<g.length;G++){const Q=E[G];Q!==null&&(E[G]=null,g[G].disconnect(Q))}A=null,Z=null,M.reset(),t.setRenderTarget(f),m=null,d=null,u=null,r=null,y=null,Pt.stop(),n.isPresenting=!1,t.setPixelRatio(w),t.setSize(P.width,P.height,!1),n.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(G){s=G,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(G){a=G,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return c||o},this.setReferenceSpace=function(G){c=G},this.getBaseLayer=function(){return d!==null?d:m},this.getBinding=function(){return u},this.getFrame=function(){return _},this.getSession=function(){return r},this.setSession=async function(G){if(r=G,r!==null){if(f=t.getRenderTarget(),r.addEventListener("select",K),r.addEventListener("selectstart",K),r.addEventListener("selectend",K),r.addEventListener("squeeze",K),r.addEventListener("squeezestart",K),r.addEventListener("squeezeend",K),r.addEventListener("end",L),r.addEventListener("inputsourceschange",k),p.xrCompatible!==!0&&await e.makeXRCompatible(),w=t.getPixelRatio(),t.getSize(P),r.renderState.layers===void 0||t.capabilities.isWebGL2===!1){const Q={antialias:r.renderState.layers===void 0?p.antialias:!0,alpha:!0,depth:p.depth,stencil:p.stencil,framebufferScaleFactor:s};m=new XRWebGLLayer(r,e,Q),r.updateRenderState({baseLayer:m}),t.setPixelRatio(1),t.setSize(m.framebufferWidth,m.framebufferHeight,!1),y=new Ln(m.framebufferWidth,m.framebufferHeight,{format:Fe,type:fn,colorSpace:t.outputColorSpace,stencilBuffer:p.stencil})}else{let Q=null,pt=null,Tt=null;p.depth&&(Tt=p.stencil?e.DEPTH24_STENCIL8:e.DEPTH_COMPONENT24,Q=p.stencil?ai:Pn,pt=p.stencil?Cn:cn);const Mt={colorFormat:e.RGBA8,depthFormat:Tt,scaleFactor:s};u=new XRWebGLBinding(r,e),d=u.createProjectionLayer(Mt),r.updateRenderState({layers:[d]}),t.setPixelRatio(1),t.setSize(d.textureWidth,d.textureHeight,!1),y=new Ln(d.textureWidth,d.textureHeight,{format:Fe,type:fn,depthTexture:new el(d.textureWidth,d.textureHeight,pt,void 0,void 0,void 0,void 0,void 0,void 0,Q),stencilBuffer:p.stencil,colorSpace:t.outputColorSpace,samples:p.antialias?4:0});const vt=t.properties.get(y);vt.__ignoreDepthValues=d.ignoreDepthValues}y.isXRRenderTarget=!0,this.setFoveation(l),c=null,o=await r.requestReferenceSpace(a),Pt.setContext(r),Pt.start(),n.isPresenting=!0,n.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(r!==null)return r.environmentBlendMode};function k(G){for(let Q=0;Q<G.removed.length;Q++){const pt=G.removed[Q],Tt=E.indexOf(pt);Tt>=0&&(E[Tt]=null,g[Tt].disconnect(pt))}for(let Q=0;Q<G.added.length;Q++){const pt=G.added[Q];let Tt=E.indexOf(pt);if(Tt===-1){for(let vt=0;vt<g.length;vt++)if(vt>=E.length){E.push(pt),Tt=vt;break}else if(E[vt]===null){E[vt]=pt,Tt=vt;break}if(Tt===-1)break}const Mt=g[Tt];Mt&&Mt.connect(pt)}}const z=new C,J=new C;function X(G,Q,pt){z.setFromMatrixPosition(Q.matrixWorld),J.setFromMatrixPosition(pt.matrixWorld);const Tt=z.distanceTo(J),Mt=Q.projectionMatrix.elements,vt=pt.projectionMatrix.elements,Gt=Mt[14]/(Mt[10]-1),At=Mt[14]/(Mt[10]+1),R=(Mt[9]+1)/Mt[5],at=(Mt[9]-1)/Mt[5],Y=(Mt[8]-1)/Mt[0],rt=(vt[8]+1)/vt[0],$=Gt*Y,_t=Gt*rt,dt=Tt/(-Y+rt),xt=dt*-Y;Q.matrixWorld.decompose(G.position,G.quaternion,G.scale),G.translateX(xt),G.translateZ(dt),G.matrixWorld.compose(G.position,G.quaternion,G.scale),G.matrixWorldInverse.copy(G.matrixWorld).invert();const Vt=Gt+dt,T=At+dt,x=$-xt,H=_t+(Tt-xt),W=R*At/T*Vt,tt=at*At/T*Vt;G.projectionMatrix.makePerspective(x,H,W,tt,Vt,T),G.projectionMatrixInverse.copy(G.projectionMatrix).invert()}function q(G,Q){Q===null?G.matrixWorld.copy(G.matrix):G.matrixWorld.multiplyMatrices(Q.matrixWorld,G.matrix),G.matrixWorldInverse.copy(G.matrixWorld).invert()}this.updateCamera=function(G){if(r===null)return;M.texture!==null&&(G.near=M.depthNear,G.far=M.depthFar),v.near=U.near=b.near=G.near,v.far=U.far=b.far=G.far,(A!==v.near||Z!==v.far)&&(r.updateRenderState({depthNear:v.near,depthFar:v.far}),A=v.near,Z=v.far,b.near=A,b.far=Z,U.near=A,U.far=Z,b.updateProjectionMatrix(),U.updateProjectionMatrix(),G.updateProjectionMatrix());const Q=G.parent,pt=v.cameras;q(v,Q);for(let Tt=0;Tt<pt.length;Tt++)q(pt[Tt],Q);pt.length===2?X(v,b,U):v.projectionMatrix.copy(b.projectionMatrix),nt(G,v,Q)};function nt(G,Q,pt){pt===null?G.matrix.copy(Q.matrixWorld):(G.matrix.copy(pt.matrixWorld),G.matrix.invert(),G.matrix.multiply(Q.matrixWorld)),G.matrix.decompose(G.position,G.quaternion,G.scale),G.updateMatrixWorld(!0),G.projectionMatrix.copy(Q.projectionMatrix),G.projectionMatrixInverse.copy(Q.projectionMatrixInverse),G.isPerspectiveCamera&&(G.fov=bi*2*Math.atan(1/G.projectionMatrix.elements[5]),G.zoom=1)}this.getCamera=function(){return v},this.getFoveation=function(){if(!(d===null&&m===null))return l},this.setFoveation=function(G){l=G,d!==null&&(d.fixedFoveation=G),m!==null&&m.fixedFoveation!==void 0&&(m.fixedFoveation=G)},this.hasDepthSensing=function(){return M.texture!==null};let et=null;function gt(G,Q){if(h=Q.getViewerPose(c||o),_=Q,h!==null){const pt=h.views;m!==null&&(t.setRenderTargetFramebuffer(y,m.framebuffer),t.setRenderTarget(y));let Tt=!1;pt.length!==v.cameras.length&&(v.cameras.length=0,Tt=!0);for(let vt=0;vt<pt.length;vt++){const Gt=pt[vt];let At=null;if(m!==null)At=m.getViewport(Gt);else{const at=u.getViewSubImage(d,Gt);At=at.viewport,vt===0&&(t.setRenderTargetTextures(y,at.colorTexture,d.ignoreDepthValues?void 0:at.depthStencilTexture),t.setRenderTarget(y))}let R=V[vt];R===void 0&&(R=new Pe,R.layers.enable(vt),R.viewport=new te,V[vt]=R),R.matrix.fromArray(Gt.transform.matrix),R.matrix.decompose(R.position,R.quaternion,R.scale),R.projectionMatrix.fromArray(Gt.projectionMatrix),R.projectionMatrixInverse.copy(R.projectionMatrix).invert(),R.viewport.set(At.x,At.y,At.width,At.height),vt===0&&(v.matrix.copy(R.matrix),v.matrix.decompose(v.position,v.quaternion,v.scale)),Tt===!0&&v.cameras.push(R)}const Mt=r.enabledFeatures;if(Mt&&Mt.includes("depth-sensing")){const vt=u.getDepthInformation(pt[0]);vt&&vt.isValid&&vt.texture&&M.init(t,vt,r.renderState)}}for(let pt=0;pt<g.length;pt++){const Tt=E[pt],Mt=g[pt];Tt!==null&&Mt!==void 0&&Mt.update(Tt,Q,c||o)}M.render(t,v),et&&et(G,Q),Q.detectedPlanes&&n.dispatchEvent({type:"planesdetected",data:Q}),_=null}const Pt=new Qo;Pt.setAnimationLoop(gt),this.setAnimationLoop=function(G){et=G},this.dispose=function(){}}}const En=new ke,$p=new Jt;function jp(i,t){function e(p,f){p.matrixAutoUpdate===!0&&p.updateMatrix(),f.value.copy(p.matrix)}function n(p,f){f.color.getRGB(p.fogColor.value,Ko(i)),f.isFog?(p.fogNear.value=f.near,p.fogFar.value=f.far):f.isFogExp2&&(p.fogDensity.value=f.density)}function r(p,f,y,g,E){f.isMeshBasicMaterial||f.isMeshLambertMaterial?s(p,f):f.isMeshToonMaterial?(s(p,f),u(p,f)):f.isMeshPhongMaterial?(s(p,f),h(p,f)):f.isMeshStandardMaterial?(s(p,f),d(p,f),f.isMeshPhysicalMaterial&&m(p,f,E)):f.isMeshMatcapMaterial?(s(p,f),_(p,f)):f.isMeshDepthMaterial?s(p,f):f.isMeshDistanceMaterial?(s(p,f),M(p,f)):f.isMeshNormalMaterial?s(p,f):f.isLineBasicMaterial?(o(p,f),f.isLineDashedMaterial&&a(p,f)):f.isPointsMaterial?l(p,f,y,g):f.isSpriteMaterial?c(p,f):f.isShadowMaterial?(p.color.value.copy(f.color),p.opacity.value=f.opacity):f.isShaderMaterial&&(f.uniformsNeedUpdate=!1)}function s(p,f){p.opacity.value=f.opacity,f.color&&p.diffuse.value.copy(f.color),f.emissive&&p.emissive.value.copy(f.emissive).multiplyScalar(f.emissiveIntensity),f.map&&(p.map.value=f.map,e(f.map,p.mapTransform)),f.alphaMap&&(p.alphaMap.value=f.alphaMap,e(f.alphaMap,p.alphaMapTransform)),f.bumpMap&&(p.bumpMap.value=f.bumpMap,e(f.bumpMap,p.bumpMapTransform),p.bumpScale.value=f.bumpScale,f.side===Ee&&(p.bumpScale.value*=-1)),f.normalMap&&(p.normalMap.value=f.normalMap,e(f.normalMap,p.normalMapTransform),p.normalScale.value.copy(f.normalScale),f.side===Ee&&p.normalScale.value.negate()),f.displacementMap&&(p.displacementMap.value=f.displacementMap,e(f.displacementMap,p.displacementMapTransform),p.displacementScale.value=f.displacementScale,p.displacementBias.value=f.displacementBias),f.emissiveMap&&(p.emissiveMap.value=f.emissiveMap,e(f.emissiveMap,p.emissiveMapTransform)),f.specularMap&&(p.specularMap.value=f.specularMap,e(f.specularMap,p.specularMapTransform)),f.alphaTest>0&&(p.alphaTest.value=f.alphaTest);const y=t.get(f),g=y.envMap,E=y.envMapRotation;if(g&&(p.envMap.value=g,En.copy(E),En.x*=-1,En.y*=-1,En.z*=-1,g.isCubeTexture&&g.isRenderTargetTexture===!1&&(En.y*=-1,En.z*=-1),p.envMapRotation.value.setFromMatrix4($p.makeRotationFromEuler(En)),p.flipEnvMap.value=g.isCubeTexture&&g.isRenderTargetTexture===!1?-1:1,p.reflectivity.value=f.reflectivity,p.ior.value=f.ior,p.refractionRatio.value=f.refractionRatio),f.lightMap){p.lightMap.value=f.lightMap;const P=i._useLegacyLights===!0?Math.PI:1;p.lightMapIntensity.value=f.lightMapIntensity*P,e(f.lightMap,p.lightMapTransform)}f.aoMap&&(p.aoMap.value=f.aoMap,p.aoMapIntensity.value=f.aoMapIntensity,e(f.aoMap,p.aoMapTransform))}function o(p,f){p.diffuse.value.copy(f.color),p.opacity.value=f.opacity,f.map&&(p.map.value=f.map,e(f.map,p.mapTransform))}function a(p,f){p.dashSize.value=f.dashSize,p.totalSize.value=f.dashSize+f.gapSize,p.scale.value=f.scale}function l(p,f,y,g){p.diffuse.value.copy(f.color),p.opacity.value=f.opacity,p.size.value=f.size*y,p.scale.value=g*.5,f.map&&(p.map.value=f.map,e(f.map,p.uvTransform)),f.alphaMap&&(p.alphaMap.value=f.alphaMap,e(f.alphaMap,p.alphaMapTransform)),f.alphaTest>0&&(p.alphaTest.value=f.alphaTest)}function c(p,f){p.diffuse.value.copy(f.color),p.opacity.value=f.opacity,p.rotation.value=f.rotation,f.map&&(p.map.value=f.map,e(f.map,p.mapTransform)),f.alphaMap&&(p.alphaMap.value=f.alphaMap,e(f.alphaMap,p.alphaMapTransform)),f.alphaTest>0&&(p.alphaTest.value=f.alphaTest)}function h(p,f){p.specular.value.copy(f.specular),p.shininess.value=Math.max(f.shininess,1e-4)}function u(p,f){f.gradientMap&&(p.gradientMap.value=f.gradientMap)}function d(p,f){p.metalness.value=f.metalness,f.metalnessMap&&(p.metalnessMap.value=f.metalnessMap,e(f.metalnessMap,p.metalnessMapTransform)),p.roughness.value=f.roughness,f.roughnessMap&&(p.roughnessMap.value=f.roughnessMap,e(f.roughnessMap,p.roughnessMapTransform)),t.get(f).envMap&&(p.envMapIntensity.value=f.envMapIntensity)}function m(p,f,y){p.ior.value=f.ior,f.sheen>0&&(p.sheenColor.value.copy(f.sheenColor).multiplyScalar(f.sheen),p.sheenRoughness.value=f.sheenRoughness,f.sheenColorMap&&(p.sheenColorMap.value=f.sheenColorMap,e(f.sheenColorMap,p.sheenColorMapTransform)),f.sheenRoughnessMap&&(p.sheenRoughnessMap.value=f.sheenRoughnessMap,e(f.sheenRoughnessMap,p.sheenRoughnessMapTransform))),f.clearcoat>0&&(p.clearcoat.value=f.clearcoat,p.clearcoatRoughness.value=f.clearcoatRoughness,f.clearcoatMap&&(p.clearcoatMap.value=f.clearcoatMap,e(f.clearcoatMap,p.clearcoatMapTransform)),f.clearcoatRoughnessMap&&(p.clearcoatRoughnessMap.value=f.clearcoatRoughnessMap,e(f.clearcoatRoughnessMap,p.clearcoatRoughnessMapTransform)),f.clearcoatNormalMap&&(p.clearcoatNormalMap.value=f.clearcoatNormalMap,e(f.clearcoatNormalMap,p.clearcoatNormalMapTransform),p.clearcoatNormalScale.value.copy(f.clearcoatNormalScale),f.side===Ee&&p.clearcoatNormalScale.value.negate())),f.iridescence>0&&(p.iridescence.value=f.iridescence,p.iridescenceIOR.value=f.iridescenceIOR,p.iridescenceThicknessMinimum.value=f.iridescenceThicknessRange[0],p.iridescenceThicknessMaximum.value=f.iridescenceThicknessRange[1],f.iridescenceMap&&(p.iridescenceMap.value=f.iridescenceMap,e(f.iridescenceMap,p.iridescenceMapTransform)),f.iridescenceThicknessMap&&(p.iridescenceThicknessMap.value=f.iridescenceThicknessMap,e(f.iridescenceThicknessMap,p.iridescenceThicknessMapTransform))),f.transmission>0&&(p.transmission.value=f.transmission,p.transmissionSamplerMap.value=y.texture,p.transmissionSamplerSize.value.set(y.width,y.height),f.transmissionMap&&(p.transmissionMap.value=f.transmissionMap,e(f.transmissionMap,p.transmissionMapTransform)),p.thickness.value=f.thickness,f.thicknessMap&&(p.thicknessMap.value=f.thicknessMap,e(f.thicknessMap,p.thicknessMapTransform)),p.attenuationDistance.value=f.attenuationDistance,p.attenuationColor.value.copy(f.attenuationColor)),f.anisotropy>0&&(p.anisotropyVector.value.set(f.anisotropy*Math.cos(f.anisotropyRotation),f.anisotropy*Math.sin(f.anisotropyRotation)),f.anisotropyMap&&(p.anisotropyMap.value=f.anisotropyMap,e(f.anisotropyMap,p.anisotropyMapTransform))),p.specularIntensity.value=f.specularIntensity,p.specularColor.value.copy(f.specularColor),f.specularColorMap&&(p.specularColorMap.value=f.specularColorMap,e(f.specularColorMap,p.specularColorMapTransform)),f.specularIntensityMap&&(p.specularIntensityMap.value=f.specularIntensityMap,e(f.specularIntensityMap,p.specularIntensityMapTransform))}function _(p,f){f.matcap&&(p.matcap.value=f.matcap)}function M(p,f){const y=t.get(f).light;p.referencePosition.value.setFromMatrixPosition(y.matrixWorld),p.nearDistance.value=y.shadow.camera.near,p.farDistance.value=y.shadow.camera.far}return{refreshFogUniforms:n,refreshMaterialUniforms:r}}function Qp(i,t,e,n){let r={},s={},o=[];const a=e.isWebGL2?i.getParameter(i.MAX_UNIFORM_BUFFER_BINDINGS):0;function l(y,g){const E=g.program;n.uniformBlockBinding(y,E)}function c(y,g){let E=r[y.id];E===void 0&&(_(y),E=h(y),r[y.id]=E,y.addEventListener("dispose",p));const P=g.program;n.updateUBOMapping(y,P);const w=t.render.frame;s[y.id]!==w&&(d(y),s[y.id]=w)}function h(y){const g=u();y.__bindingPointIndex=g;const E=i.createBuffer(),P=y.__size,w=y.usage;return i.bindBuffer(i.UNIFORM_BUFFER,E),i.bufferData(i.UNIFORM_BUFFER,P,w),i.bindBuffer(i.UNIFORM_BUFFER,null),i.bindBufferBase(i.UNIFORM_BUFFER,g,E),E}function u(){for(let y=0;y<a;y++)if(o.indexOf(y)===-1)return o.push(y),y;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function d(y){const g=r[y.id],E=y.uniforms,P=y.__cache;i.bindBuffer(i.UNIFORM_BUFFER,g);for(let w=0,b=E.length;w<b;w++){const U=Array.isArray(E[w])?E[w]:[E[w]];for(let V=0,v=U.length;V<v;V++){const A=U[V];if(m(A,w,V,P)===!0){const Z=A.__offset,K=Array.isArray(A.value)?A.value:[A.value];let L=0;for(let k=0;k<K.length;k++){const z=K[k],J=M(z);typeof z=="number"||typeof z=="boolean"?(A.__data[0]=z,i.bufferSubData(i.UNIFORM_BUFFER,Z+L,A.__data)):z.isMatrix3?(A.__data[0]=z.elements[0],A.__data[1]=z.elements[1],A.__data[2]=z.elements[2],A.__data[3]=0,A.__data[4]=z.elements[3],A.__data[5]=z.elements[4],A.__data[6]=z.elements[5],A.__data[7]=0,A.__data[8]=z.elements[6],A.__data[9]=z.elements[7],A.__data[10]=z.elements[8],A.__data[11]=0):(z.toArray(A.__data,L),L+=J.storage/Float32Array.BYTES_PER_ELEMENT)}i.bufferSubData(i.UNIFORM_BUFFER,Z,A.__data)}}}i.bindBuffer(i.UNIFORM_BUFFER,null)}function m(y,g,E,P){const w=y.value,b=g+"_"+E;if(P[b]===void 0)return typeof w=="number"||typeof w=="boolean"?P[b]=w:P[b]=w.clone(),!0;{const U=P[b];if(typeof w=="number"||typeof w=="boolean"){if(U!==w)return P[b]=w,!0}else if(U.equals(w)===!1)return U.copy(w),!0}return!1}function _(y){const g=y.uniforms;let E=0;const P=16;for(let b=0,U=g.length;b<U;b++){const V=Array.isArray(g[b])?g[b]:[g[b]];for(let v=0,A=V.length;v<A;v++){const Z=V[v],K=Array.isArray(Z.value)?Z.value:[Z.value];for(let L=0,k=K.length;L<k;L++){const z=K[L],J=M(z),X=E%P;X!==0&&P-X<J.boundary&&(E+=P-X),Z.__data=new Float32Array(J.storage/Float32Array.BYTES_PER_ELEMENT),Z.__offset=E,E+=J.storage}}}const w=E%P;return w>0&&(E+=P-w),y.__size=E,y.__cache={},this}function M(y){const g={boundary:0,storage:0};return typeof y=="number"||typeof y=="boolean"?(g.boundary=4,g.storage=4):y.isVector2?(g.boundary=8,g.storage=8):y.isVector3||y.isColor?(g.boundary=16,g.storage=12):y.isVector4?(g.boundary=16,g.storage=16):y.isMatrix3?(g.boundary=48,g.storage=48):y.isMatrix4?(g.boundary=64,g.storage=64):y.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",y),g}function p(y){const g=y.target;g.removeEventListener("dispose",p);const E=o.indexOf(g.__bindingPointIndex);o.splice(E,1),i.deleteBuffer(r[g.id]),delete r[g.id],delete s[g.id]}function f(){for(const y in r)i.deleteBuffer(r[y]);o=[],r={},s={}}return{bind:l,update:c,dispose:f}}class tm{constructor(t={}){const{canvas:e=Hc(),context:n=null,depth:r=!0,stencil:s=!0,alpha:o=!1,antialias:a=!1,premultipliedAlpha:l=!0,preserveDrawingBuffer:c=!1,powerPreference:h="default",failIfMajorPerformanceCaveat:u=!1}=t;this.isWebGLRenderer=!0;let d;n!==null?d=n.getContextAttributes().alpha:d=o;const m=new Uint32Array(4),_=new Int32Array(4);let M=null,p=null;const f=[],y=[];this.domElement=e,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this._outputColorSpace=ze,this._useLegacyLights=!1,this.toneMapping=un,this.toneMappingExposure=1;const g=this;let E=!1,P=0,w=0,b=null,U=-1,V=null;const v=new te,A=new te;let Z=null;const K=new zt(0);let L=0,k=e.width,z=e.height,J=1,X=null,q=null;const nt=new te(0,0,k,z),et=new te(0,0,k,z);let gt=!1;const Pt=new Cs;let G=!1,Q=!1,pt=null;const Tt=new Jt,Mt=new it,vt=new C,Gt={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0};function At(){return b===null?J:1}let R=n;function at(S,I){for(let O=0;O<S.length;O++){const B=S[O],N=e.getContext(B,I);if(N!==null)return N}return null}try{const S={alpha:!0,depth:r,stencil:s,antialias:a,premultipliedAlpha:l,preserveDrawingBuffer:c,powerPreference:h,failIfMajorPerformanceCaveat:u};if("setAttribute"in e&&e.setAttribute("data-engine",`three.js r${Es}`),e.addEventListener("webglcontextlost",jt,!1),e.addEventListener("webglcontextrestored",D,!1),e.addEventListener("webglcontextcreationerror",ut,!1),R===null){const I=["webgl2","webgl","experimental-webgl"];if(g.isWebGL1Renderer===!0&&I.shift(),R=at(I,S),R===null)throw at(I)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}typeof WebGLRenderingContext<"u"&&R instanceof WebGLRenderingContext&&console.warn("THREE.WebGLRenderer: WebGL 1 support was deprecated in r153 and will be removed in r163."),R.getShaderPrecisionFormat===void 0&&(R.getShaderPrecisionFormat=function(){return{rangeMin:1,rangeMax:1,precision:1}})}catch(S){throw console.error("THREE.WebGLRenderer: "+S.message),S}let Y,rt,$,_t,dt,xt,Vt,T,x,H,W,tt,j,Lt,wt,lt,ht,Dt,st,re,kt,bt,St,yt;function Xt(){Y=new sd(R),rt=new Qf(R,Y,t),Y.init(rt),bt=new Wp(R,Y,rt),$=new Vp(R,Y,rt),_t=new ld(R),dt=new Rp,xt=new kp(R,Y,$,dt,rt,bt,_t),Vt=new ed(g),T=new rd(g),x=new dh(R,rt),St=new $f(R,Y,x,rt),H=new ad(R,x,_t,St),W=new fd(R,H,x,_t),st=new ud(R,rt,xt),lt=new td(dt),tt=new wp(g,Vt,T,Y,rt,St,lt),j=new jp(g,dt),Lt=new Pp,wt=new Fp(Y,rt),Dt=new Kf(g,Vt,T,$,W,d,l),ht=new Hp(g,W,rt),yt=new Qp(R,_t,rt,$),re=new jf(R,Y,_t,rt),kt=new od(R,Y,_t,rt),_t.programs=tt.programs,g.capabilities=rt,g.extensions=Y,g.properties=dt,g.renderLists=Lt,g.shadowMap=ht,g.state=$,g.info=_t}Xt();const It=new Kp(g,R);this.xr=It,this.getContext=function(){return R},this.getContextAttributes=function(){return R.getContextAttributes()},this.forceContextLoss=function(){const S=Y.get("WEBGL_lose_context");S&&S.loseContext()},this.forceContextRestore=function(){const S=Y.get("WEBGL_lose_context");S&&S.restoreContext()},this.getPixelRatio=function(){return J},this.setPixelRatio=function(S){S!==void 0&&(J=S,this.setSize(k,z,!1))},this.getSize=function(S){return S.set(k,z)},this.setSize=function(S,I,O=!0){if(It.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}k=S,z=I,e.width=Math.floor(S*J),e.height=Math.floor(I*J),O===!0&&(e.style.width=S+"px",e.style.height=I+"px"),this.setViewport(0,0,S,I)},this.getDrawingBufferSize=function(S){return S.set(k*J,z*J).floor()},this.setDrawingBufferSize=function(S,I,O){k=S,z=I,J=O,e.width=Math.floor(S*O),e.height=Math.floor(I*O),this.setViewport(0,0,S,I)},this.getCurrentViewport=function(S){return S.copy(v)},this.getViewport=function(S){return S.copy(nt)},this.setViewport=function(S,I,O,B){S.isVector4?nt.set(S.x,S.y,S.z,S.w):nt.set(S,I,O,B),$.viewport(v.copy(nt).multiplyScalar(J).round())},this.getScissor=function(S){return S.copy(et)},this.setScissor=function(S,I,O,B){S.isVector4?et.set(S.x,S.y,S.z,S.w):et.set(S,I,O,B),$.scissor(A.copy(et).multiplyScalar(J).round())},this.getScissorTest=function(){return gt},this.setScissorTest=function(S){$.setScissorTest(gt=S)},this.setOpaqueSort=function(S){X=S},this.setTransparentSort=function(S){q=S},this.getClearColor=function(S){return S.copy(Dt.getClearColor())},this.setClearColor=function(){Dt.setClearColor.apply(Dt,arguments)},this.getClearAlpha=function(){return Dt.getClearAlpha()},this.setClearAlpha=function(){Dt.setClearAlpha.apply(Dt,arguments)},this.clear=function(S=!0,I=!0,O=!0){let B=0;if(S){let N=!1;if(b!==null){const mt=b.texture.format;N=mt===Bo||mt===Oo||mt===Fo}if(N){const mt=b.texture.type,Et=mt===fn||mt===cn||mt===Ts||mt===Cn||mt===Uo||mt===Io,Rt=Dt.getClearColor(),Ct=Dt.getClearAlpha(),Ht=Rt.r,Ut=Rt.g,Nt=Rt.b;Et?(m[0]=Ht,m[1]=Ut,m[2]=Nt,m[3]=Ct,R.clearBufferuiv(R.COLOR,0,m)):(_[0]=Ht,_[1]=Ut,_[2]=Nt,_[3]=Ct,R.clearBufferiv(R.COLOR,0,_))}else B|=R.COLOR_BUFFER_BIT}I&&(B|=R.DEPTH_BUFFER_BIT),O&&(B|=R.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),R.clear(B)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){e.removeEventListener("webglcontextlost",jt,!1),e.removeEventListener("webglcontextrestored",D,!1),e.removeEventListener("webglcontextcreationerror",ut,!1),Lt.dispose(),wt.dispose(),dt.dispose(),Vt.dispose(),T.dispose(),W.dispose(),St.dispose(),yt.dispose(),tt.dispose(),It.dispose(),It.removeEventListener("sessionstart",we),It.removeEventListener("sessionend",Kt),pt&&(pt.dispose(),pt=null),xe.stop()};function jt(S){S.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),E=!0}function D(){console.log("THREE.WebGLRenderer: Context Restored."),E=!1;const S=_t.autoReset,I=ht.enabled,O=ht.autoUpdate,B=ht.needsUpdate,N=ht.type;Xt(),_t.autoReset=S,ht.enabled=I,ht.autoUpdate=O,ht.needsUpdate=B,ht.type=N}function ut(S){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",S.statusMessage)}function F(S){const I=S.target;I.removeEventListener("dispose",F),ot(I)}function ot(S){ft(S),dt.remove(S)}function ft(S){const I=dt.get(S).programs;I!==void 0&&(I.forEach(function(O){tt.releaseProgram(O)}),S.isShaderMaterial&&tt.releaseShaderCache(S))}this.renderBufferDirect=function(S,I,O,B,N,mt){I===null&&(I=Gt);const Et=N.isMesh&&N.matrixWorld.determinant()<0,Rt=Al(S,I,O,B,N);$.setMaterial(B,Et);let Ct=O.index,Ht=1;if(B.wireframe===!0){if(Ct=H.getWireframeAttribute(O),Ct===void 0)return;Ht=2}const Ut=O.drawRange,Nt=O.attributes.position;let ie=Ut.start*Ht,Te=(Ut.start+Ut.count)*Ht;mt!==null&&(ie=Math.max(ie,mt.start*Ht),Te=Math.min(Te,(mt.start+mt.count)*Ht)),Ct!==null?(ie=Math.max(ie,0),Te=Math.min(Te,Ct.count)):Nt!=null&&(ie=Math.max(ie,0),Te=Math.min(Te,Nt.count));const ce=Te-ie;if(ce<0||ce===1/0)return;St.setup(N,B,Rt,O,Ct);let Xe,ee=re;if(Ct!==null&&(Xe=x.get(Ct),ee=kt,ee.setIndex(Xe)),N.isMesh)B.wireframe===!0?($.setLineWidth(B.wireframeLinewidth*At()),ee.setMode(R.LINES)):ee.setMode(R.TRIANGLES);else if(N.isLine){let Ft=B.linewidth;Ft===void 0&&(Ft=1),$.setLineWidth(Ft*At()),N.isLineSegments?ee.setMode(R.LINES):N.isLineLoop?ee.setMode(R.LINE_LOOP):ee.setMode(R.LINE_STRIP)}else N.isPoints?ee.setMode(R.POINTS):N.isSprite&&ee.setMode(R.TRIANGLES);if(N.isBatchedMesh)ee.renderMultiDraw(N._multiDrawStarts,N._multiDrawCounts,N._multiDrawCount);else if(N.isInstancedMesh)ee.renderInstances(ie,ce,N.count);else if(O.isInstancedBufferGeometry){const Ft=O._maxInstanceCount!==void 0?O._maxInstanceCount:1/0,Er=Math.min(O.instanceCount,Ft);ee.renderInstances(ie,ce,Er)}else ee.render(ie,ce)};function Wt(S,I,O){S.transparent===!0&&S.side===je&&S.forceSinglePass===!1?(S.side=Ee,S.needsUpdate=!0,Ui(S,I,O),S.side=pn,S.needsUpdate=!0,Ui(S,I,O),S.side=je):Ui(S,I,O)}this.compile=function(S,I,O=null){O===null&&(O=S),p=wt.get(O),p.init(),y.push(p),O.traverseVisible(function(N){N.isLight&&N.layers.test(I.layers)&&(p.pushLight(N),N.castShadow&&p.pushShadow(N))}),S!==O&&S.traverseVisible(function(N){N.isLight&&N.layers.test(I.layers)&&(p.pushLight(N),N.castShadow&&p.pushShadow(N))}),p.setupLights(g._useLegacyLights);const B=new Set;return S.traverse(function(N){const mt=N.material;if(mt)if(Array.isArray(mt))for(let Et=0;Et<mt.length;Et++){const Rt=mt[Et];Wt(Rt,O,N),B.add(Rt)}else Wt(mt,O,N),B.add(mt)}),y.pop(),p=null,B},this.compileAsync=function(S,I,O=null){const B=this.compile(S,I,O);return new Promise(N=>{function mt(){if(B.forEach(function(Et){dt.get(Et).currentProgram.isReady()&&B.delete(Et)}),B.size===0){N(S);return}setTimeout(mt,10)}Y.get("KHR_parallel_shader_compile")!==null?mt():setTimeout(mt,10)})};let Zt=null;function fe(S){Zt&&Zt(S)}function we(){xe.stop()}function Kt(){xe.start()}const xe=new Qo;xe.setAnimationLoop(fe),typeof self<"u"&&xe.setContext(self),this.setAnimationLoop=function(S){Zt=S,It.setAnimationLoop(S),S===null?xe.stop():xe.start()},It.addEventListener("sessionstart",we),It.addEventListener("sessionend",Kt),this.render=function(S,I){if(I!==void 0&&I.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(E===!0)return;S.matrixWorldAutoUpdate===!0&&S.updateMatrixWorld(),I.parent===null&&I.matrixWorldAutoUpdate===!0&&I.updateMatrixWorld(),It.enabled===!0&&It.isPresenting===!0&&(It.cameraAutoUpdate===!0&&It.updateCamera(I),I=It.getCamera()),S.isScene===!0&&S.onBeforeRender(g,S,I,b),p=wt.get(S,y.length),p.init(),y.push(p),Tt.multiplyMatrices(I.projectionMatrix,I.matrixWorldInverse),Pt.setFromProjectionMatrix(Tt),Q=this.localClippingEnabled,G=lt.init(this.clippingPlanes,Q),M=Lt.get(S,f.length),M.init(),f.push(M),Be(S,I,0,g.sortObjects),M.finish(),g.sortObjects===!0&&M.sort(X,q),this.info.render.frame++,G===!0&&lt.beginShadows();const O=p.state.shadowsArray;if(ht.render(O,S,I),G===!0&&lt.endShadows(),this.info.autoReset===!0&&this.info.reset(),(It.enabled===!1||It.isPresenting===!1||It.hasDepthSensing()===!1)&&Dt.render(M,S),p.setupLights(g._useLegacyLights),I.isArrayCamera){const B=I.cameras;for(let N=0,mt=B.length;N<mt;N++){const Et=B[N];Ns(M,S,Et,Et.viewport)}}else Ns(M,S,I);b!==null&&(xt.updateMultisampleRenderTarget(b),xt.updateRenderTargetMipmap(b)),S.isScene===!0&&S.onAfterRender(g,S,I),St.resetDefaultState(),U=-1,V=null,y.pop(),y.length>0?p=y[y.length-1]:p=null,f.pop(),f.length>0?M=f[f.length-1]:M=null};function Be(S,I,O,B){if(S.visible===!1)return;if(S.layers.test(I.layers)){if(S.isGroup)O=S.renderOrder;else if(S.isLOD)S.autoUpdate===!0&&S.update(I);else if(S.isLight)p.pushLight(S),S.castShadow&&p.pushShadow(S);else if(S.isSprite){if(!S.frustumCulled||Pt.intersectsSprite(S)){B&&vt.setFromMatrixPosition(S.matrixWorld).applyMatrix4(Tt);const Et=W.update(S),Rt=S.material;Rt.visible&&M.push(S,Et,Rt,O,vt.z,null)}}else if((S.isMesh||S.isLine||S.isPoints)&&(!S.frustumCulled||Pt.intersectsObject(S))){const Et=W.update(S),Rt=S.material;if(B&&(S.boundingSphere!==void 0?(S.boundingSphere===null&&S.computeBoundingSphere(),vt.copy(S.boundingSphere.center)):(Et.boundingSphere===null&&Et.computeBoundingSphere(),vt.copy(Et.boundingSphere.center)),vt.applyMatrix4(S.matrixWorld).applyMatrix4(Tt)),Array.isArray(Rt)){const Ct=Et.groups;for(let Ht=0,Ut=Ct.length;Ht<Ut;Ht++){const Nt=Ct[Ht],ie=Rt[Nt.materialIndex];ie&&ie.visible&&M.push(S,Et,ie,O,vt.z,Nt)}}else Rt.visible&&M.push(S,Et,Rt,O,vt.z,null)}}const mt=S.children;for(let Et=0,Rt=mt.length;Et<Rt;Et++)Be(mt[Et],I,O,B)}function Ns(S,I,O,B){const N=S.opaque,mt=S.transmissive,Et=S.transparent;p.setupLightsView(O),G===!0&&lt.setGlobalState(g.clippingPlanes,O),mt.length>0&&Tl(N,mt,I,O),B&&$.viewport(v.copy(B)),N.length>0&&Di(N,I,O),mt.length>0&&Di(mt,I,O),Et.length>0&&Di(Et,I,O),$.buffers.depth.setTest(!0),$.buffers.depth.setMask(!0),$.buffers.color.setMask(!0),$.setPolygonOffset(!1)}function Tl(S,I,O,B){if((O.isScene===!0?O.overrideMaterial:null)!==null)return;const mt=rt.isWebGL2;pt===null&&(pt=new Ln(1,1,{generateMipmaps:!0,type:Y.has("EXT_color_buffer_half_float")?Ai:fn,minFilter:Rn,samples:mt?4:0})),g.getDrawingBufferSize(Mt),mt?pt.setSize(Mt.x,Mt.y):pt.setSize(dr(Mt.x),dr(Mt.y));const Et=g.getRenderTarget();g.setRenderTarget(pt),g.getClearColor(K),L=g.getClearAlpha(),L<1&&g.setClearColor(16777215,.5),g.clear();const Rt=g.toneMapping;g.toneMapping=un,Di(S,O,B),xt.updateMultisampleRenderTarget(pt),xt.updateRenderTargetMipmap(pt);let Ct=!1;for(let Ht=0,Ut=I.length;Ht<Ut;Ht++){const Nt=I[Ht],ie=Nt.object,Te=Nt.geometry,ce=Nt.material,Xe=Nt.group;if(ce.side===je&&ie.layers.test(B.layers)){const ee=ce.side;ce.side=Ee,ce.needsUpdate=!0,Fs(ie,O,B,Te,ce,Xe),ce.side=ee,ce.needsUpdate=!0,Ct=!0}}Ct===!0&&(xt.updateMultisampleRenderTarget(pt),xt.updateRenderTargetMipmap(pt)),g.setRenderTarget(Et),g.setClearColor(K,L),g.toneMapping=Rt}function Di(S,I,O){const B=I.isScene===!0?I.overrideMaterial:null;for(let N=0,mt=S.length;N<mt;N++){const Et=S[N],Rt=Et.object,Ct=Et.geometry,Ht=B===null?Et.material:B,Ut=Et.group;Rt.layers.test(O.layers)&&Fs(Rt,I,O,Ct,Ht,Ut)}}function Fs(S,I,O,B,N,mt){S.onBeforeRender(g,I,O,B,N,mt),S.modelViewMatrix.multiplyMatrices(O.matrixWorldInverse,S.matrixWorld),S.normalMatrix.getNormalMatrix(S.modelViewMatrix),N.onBeforeRender(g,I,O,B,S,mt),N.transparent===!0&&N.side===je&&N.forceSinglePass===!1?(N.side=Ee,N.needsUpdate=!0,g.renderBufferDirect(O,I,B,N,S,mt),N.side=pn,N.needsUpdate=!0,g.renderBufferDirect(O,I,B,N,S,mt),N.side=je):g.renderBufferDirect(O,I,B,N,S,mt),S.onAfterRender(g,I,O,B,N,mt)}function Ui(S,I,O){I.isScene!==!0&&(I=Gt);const B=dt.get(S),N=p.state.lights,mt=p.state.shadowsArray,Et=N.state.version,Rt=tt.getParameters(S,N.state,mt,I,O),Ct=tt.getProgramCacheKey(Rt);let Ht=B.programs;B.environment=S.isMeshStandardMaterial?I.environment:null,B.fog=I.fog,B.envMap=(S.isMeshStandardMaterial?T:Vt).get(S.envMap||B.environment),B.envMapRotation=B.environment!==null&&S.envMap===null?I.environmentRotation:S.envMapRotation,Ht===void 0&&(S.addEventListener("dispose",F),Ht=new Map,B.programs=Ht);let Ut=Ht.get(Ct);if(Ut!==void 0){if(B.currentProgram===Ut&&B.lightsStateVersion===Et)return Bs(S,Rt),Ut}else Rt.uniforms=tt.getUniforms(S),S.onBuild(O,Rt,g),S.onBeforeCompile(Rt,g),Ut=tt.acquireProgram(Rt,Ct),Ht.set(Ct,Ut),B.uniforms=Rt.uniforms;const Nt=B.uniforms;return(!S.isShaderMaterial&&!S.isRawShaderMaterial||S.clipping===!0)&&(Nt.clippingPlanes=lt.uniform),Bs(S,Rt),B.needsLights=wl(S),B.lightsStateVersion=Et,B.needsLights&&(Nt.ambientLightColor.value=N.state.ambient,Nt.lightProbe.value=N.state.probe,Nt.directionalLights.value=N.state.directional,Nt.directionalLightShadows.value=N.state.directionalShadow,Nt.spotLights.value=N.state.spot,Nt.spotLightShadows.value=N.state.spotShadow,Nt.rectAreaLights.value=N.state.rectArea,Nt.ltc_1.value=N.state.rectAreaLTC1,Nt.ltc_2.value=N.state.rectAreaLTC2,Nt.pointLights.value=N.state.point,Nt.pointLightShadows.value=N.state.pointShadow,Nt.hemisphereLights.value=N.state.hemi,Nt.directionalShadowMap.value=N.state.directionalShadowMap,Nt.directionalShadowMatrix.value=N.state.directionalShadowMatrix,Nt.spotShadowMap.value=N.state.spotShadowMap,Nt.spotLightMatrix.value=N.state.spotLightMatrix,Nt.spotLightMap.value=N.state.spotLightMap,Nt.pointShadowMap.value=N.state.pointShadowMap,Nt.pointShadowMatrix.value=N.state.pointShadowMatrix),B.currentProgram=Ut,B.uniformsList=null,Ut}function Os(S){if(S.uniformsList===null){const I=S.currentProgram.getUniforms();S.uniformsList=or.seqWithValue(I.seq,S.uniforms)}return S.uniformsList}function Bs(S,I){const O=dt.get(S);O.outputColorSpace=I.outputColorSpace,O.batching=I.batching,O.instancing=I.instancing,O.instancingColor=I.instancingColor,O.instancingMorph=I.instancingMorph,O.skinning=I.skinning,O.morphTargets=I.morphTargets,O.morphNormals=I.morphNormals,O.morphColors=I.morphColors,O.morphTargetsCount=I.morphTargetsCount,O.numClippingPlanes=I.numClippingPlanes,O.numIntersection=I.numClipIntersection,O.vertexAlphas=I.vertexAlphas,O.vertexTangents=I.vertexTangents,O.toneMapping=I.toneMapping}function Al(S,I,O,B,N){I.isScene!==!0&&(I=Gt),xt.resetTextureUnits();const mt=I.fog,Et=B.isMeshStandardMaterial?I.environment:null,Rt=b===null?g.outputColorSpace:b.isXRRenderTarget===!0?b.texture.colorSpace:mn,Ct=(B.isMeshStandardMaterial?T:Vt).get(B.envMap||Et),Ht=B.vertexColors===!0&&!!O.attributes.color&&O.attributes.color.itemSize===4,Ut=!!O.attributes.tangent&&(!!B.normalMap||B.anisotropy>0),Nt=!!O.morphAttributes.position,ie=!!O.morphAttributes.normal,Te=!!O.morphAttributes.color;let ce=un;B.toneMapped&&(b===null||b.isXRRenderTarget===!0)&&(ce=g.toneMapping);const Xe=O.morphAttributes.position||O.morphAttributes.normal||O.morphAttributes.color,ee=Xe!==void 0?Xe.length:0,Ft=dt.get(B),Er=p.state.lights;if(G===!0&&(Q===!0||S!==V)){const Re=S===V&&B.id===U;lt.setState(B,S,Re)}let Qt=!1;B.version===Ft.__version?(Ft.needsLights&&Ft.lightsStateVersion!==Er.state.version||Ft.outputColorSpace!==Rt||N.isBatchedMesh&&Ft.batching===!1||!N.isBatchedMesh&&Ft.batching===!0||N.isInstancedMesh&&Ft.instancing===!1||!N.isInstancedMesh&&Ft.instancing===!0||N.isSkinnedMesh&&Ft.skinning===!1||!N.isSkinnedMesh&&Ft.skinning===!0||N.isInstancedMesh&&Ft.instancingColor===!0&&N.instanceColor===null||N.isInstancedMesh&&Ft.instancingColor===!1&&N.instanceColor!==null||N.isInstancedMesh&&Ft.instancingMorph===!0&&N.morphTexture===null||N.isInstancedMesh&&Ft.instancingMorph===!1&&N.morphTexture!==null||Ft.envMap!==Ct||B.fog===!0&&Ft.fog!==mt||Ft.numClippingPlanes!==void 0&&(Ft.numClippingPlanes!==lt.numPlanes||Ft.numIntersection!==lt.numIntersection)||Ft.vertexAlphas!==Ht||Ft.vertexTangents!==Ut||Ft.morphTargets!==Nt||Ft.morphNormals!==ie||Ft.morphColors!==Te||Ft.toneMapping!==ce||rt.isWebGL2===!0&&Ft.morphTargetsCount!==ee)&&(Qt=!0):(Qt=!0,Ft.__version=B.version);let gn=Ft.currentProgram;Qt===!0&&(gn=Ui(B,I,N));let zs=!1,fi=!1,Tr=!1;const me=gn.getUniforms(),_n=Ft.uniforms;if($.useProgram(gn.program)&&(zs=!0,fi=!0,Tr=!0),B.id!==U&&(U=B.id,fi=!0),zs||V!==S){me.setValue(R,"projectionMatrix",S.projectionMatrix),me.setValue(R,"viewMatrix",S.matrixWorldInverse);const Re=me.map.cameraPosition;Re!==void 0&&Re.setValue(R,vt.setFromMatrixPosition(S.matrixWorld)),rt.logarithmicDepthBuffer&&me.setValue(R,"logDepthBufFC",2/(Math.log(S.far+1)/Math.LN2)),(B.isMeshPhongMaterial||B.isMeshToonMaterial||B.isMeshLambertMaterial||B.isMeshBasicMaterial||B.isMeshStandardMaterial||B.isShaderMaterial)&&me.setValue(R,"isOrthographic",S.isOrthographicCamera===!0),V!==S&&(V=S,fi=!0,Tr=!0)}if(N.isSkinnedMesh){me.setOptional(R,N,"bindMatrix"),me.setOptional(R,N,"bindMatrixInverse");const Re=N.skeleton;Re&&(rt.floatVertexTextures?(Re.boneTexture===null&&Re.computeBoneTexture(),me.setValue(R,"boneTexture",Re.boneTexture,xt)):console.warn("THREE.WebGLRenderer: SkinnedMesh can only be used with WebGL 2. With WebGL 1 OES_texture_float and vertex textures support is required."))}N.isBatchedMesh&&(me.setOptional(R,N,"batchingTexture"),me.setValue(R,"batchingTexture",N._matricesTexture,xt));const Ar=O.morphAttributes;if((Ar.position!==void 0||Ar.normal!==void 0||Ar.color!==void 0&&rt.isWebGL2===!0)&&st.update(N,O,gn),(fi||Ft.receiveShadow!==N.receiveShadow)&&(Ft.receiveShadow=N.receiveShadow,me.setValue(R,"receiveShadow",N.receiveShadow)),B.isMeshGouraudMaterial&&B.envMap!==null&&(_n.envMap.value=Ct,_n.flipEnvMap.value=Ct.isCubeTexture&&Ct.isRenderTargetTexture===!1?-1:1),fi&&(me.setValue(R,"toneMappingExposure",g.toneMappingExposure),Ft.needsLights&&bl(_n,Tr),mt&&B.fog===!0&&j.refreshFogUniforms(_n,mt),j.refreshMaterialUniforms(_n,B,J,z,pt),or.upload(R,Os(Ft),_n,xt)),B.isShaderMaterial&&B.uniformsNeedUpdate===!0&&(or.upload(R,Os(Ft),_n,xt),B.uniformsNeedUpdate=!1),B.isSpriteMaterial&&me.setValue(R,"center",N.center),me.setValue(R,"modelViewMatrix",N.modelViewMatrix),me.setValue(R,"normalMatrix",N.normalMatrix),me.setValue(R,"modelMatrix",N.matrixWorld),B.isShaderMaterial||B.isRawShaderMaterial){const Re=B.uniformsGroups;for(let br=0,Rl=Re.length;br<Rl;br++)if(rt.isWebGL2){const Gs=Re[br];yt.update(Gs,gn),yt.bind(Gs,gn)}else console.warn("THREE.WebGLRenderer: Uniform Buffer Objects can only be used with WebGL 2.")}return gn}function bl(S,I){S.ambientLightColor.needsUpdate=I,S.lightProbe.needsUpdate=I,S.directionalLights.needsUpdate=I,S.directionalLightShadows.needsUpdate=I,S.pointLights.needsUpdate=I,S.pointLightShadows.needsUpdate=I,S.spotLights.needsUpdate=I,S.spotLightShadows.needsUpdate=I,S.rectAreaLights.needsUpdate=I,S.hemisphereLights.needsUpdate=I}function wl(S){return S.isMeshLambertMaterial||S.isMeshToonMaterial||S.isMeshPhongMaterial||S.isMeshStandardMaterial||S.isShadowMaterial||S.isShaderMaterial&&S.lights===!0}this.getActiveCubeFace=function(){return P},this.getActiveMipmapLevel=function(){return w},this.getRenderTarget=function(){return b},this.setRenderTargetTextures=function(S,I,O){dt.get(S.texture).__webglTexture=I,dt.get(S.depthTexture).__webglTexture=O;const B=dt.get(S);B.__hasExternalTextures=!0,B.__autoAllocateDepthBuffer=O===void 0,B.__autoAllocateDepthBuffer||Y.has("WEBGL_multisampled_render_to_texture")===!0&&(console.warn("THREE.WebGLRenderer: Render-to-texture extension was disabled because an external texture was provided"),B.__useRenderToTexture=!1)},this.setRenderTargetFramebuffer=function(S,I){const O=dt.get(S);O.__webglFramebuffer=I,O.__useDefaultFramebuffer=I===void 0},this.setRenderTarget=function(S,I=0,O=0){b=S,P=I,w=O;let B=!0,N=null,mt=!1,Et=!1;if(S){const Ct=dt.get(S);Ct.__useDefaultFramebuffer!==void 0?($.bindFramebuffer(R.FRAMEBUFFER,null),B=!1):Ct.__webglFramebuffer===void 0?xt.setupRenderTarget(S):Ct.__hasExternalTextures&&xt.rebindTextures(S,dt.get(S.texture).__webglTexture,dt.get(S.depthTexture).__webglTexture);const Ht=S.texture;(Ht.isData3DTexture||Ht.isDataArrayTexture||Ht.isCompressedArrayTexture)&&(Et=!0);const Ut=dt.get(S).__webglFramebuffer;S.isWebGLCubeRenderTarget?(Array.isArray(Ut[I])?N=Ut[I][O]:N=Ut[I],mt=!0):rt.isWebGL2&&S.samples>0&&xt.useMultisampledRTT(S)===!1?N=dt.get(S).__webglMultisampledFramebuffer:Array.isArray(Ut)?N=Ut[O]:N=Ut,v.copy(S.viewport),A.copy(S.scissor),Z=S.scissorTest}else v.copy(nt).multiplyScalar(J).floor(),A.copy(et).multiplyScalar(J).floor(),Z=gt;if($.bindFramebuffer(R.FRAMEBUFFER,N)&&rt.drawBuffers&&B&&$.drawBuffers(S,N),$.viewport(v),$.scissor(A),$.setScissorTest(Z),mt){const Ct=dt.get(S.texture);R.framebufferTexture2D(R.FRAMEBUFFER,R.COLOR_ATTACHMENT0,R.TEXTURE_CUBE_MAP_POSITIVE_X+I,Ct.__webglTexture,O)}else if(Et){const Ct=dt.get(S.texture),Ht=I||0;R.framebufferTextureLayer(R.FRAMEBUFFER,R.COLOR_ATTACHMENT0,Ct.__webglTexture,O||0,Ht)}U=-1},this.readRenderTargetPixels=function(S,I,O,B,N,mt,Et){if(!(S&&S.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let Rt=dt.get(S).__webglFramebuffer;if(S.isWebGLCubeRenderTarget&&Et!==void 0&&(Rt=Rt[Et]),Rt){$.bindFramebuffer(R.FRAMEBUFFER,Rt);try{const Ct=S.texture,Ht=Ct.format,Ut=Ct.type;if(Ht!==Fe&&bt.convert(Ht)!==R.getParameter(R.IMPLEMENTATION_COLOR_READ_FORMAT)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}const Nt=Ut===Ai&&(Y.has("EXT_color_buffer_half_float")||rt.isWebGL2&&Y.has("EXT_color_buffer_float"));if(Ut!==fn&&bt.convert(Ut)!==R.getParameter(R.IMPLEMENTATION_COLOR_READ_TYPE)&&!(Ut===He&&(rt.isWebGL2||Y.has("OES_texture_float")||Y.has("WEBGL_color_buffer_float")))&&!Nt){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}I>=0&&I<=S.width-B&&O>=0&&O<=S.height-N&&R.readPixels(I,O,B,N,bt.convert(Ht),bt.convert(Ut),mt)}finally{const Ct=b!==null?dt.get(b).__webglFramebuffer:null;$.bindFramebuffer(R.FRAMEBUFFER,Ct)}}},this.copyFramebufferToTexture=function(S,I,O=0){const B=Math.pow(2,-O),N=Math.floor(I.image.width*B),mt=Math.floor(I.image.height*B);xt.setTexture2D(I,0),R.copyTexSubImage2D(R.TEXTURE_2D,O,0,0,S.x,S.y,N,mt),$.unbindTexture()},this.copyTextureToTexture=function(S,I,O,B=0){const N=I.image.width,mt=I.image.height,Et=bt.convert(O.format),Rt=bt.convert(O.type);xt.setTexture2D(O,0),R.pixelStorei(R.UNPACK_FLIP_Y_WEBGL,O.flipY),R.pixelStorei(R.UNPACK_PREMULTIPLY_ALPHA_WEBGL,O.premultiplyAlpha),R.pixelStorei(R.UNPACK_ALIGNMENT,O.unpackAlignment),I.isDataTexture?R.texSubImage2D(R.TEXTURE_2D,B,S.x,S.y,N,mt,Et,Rt,I.image.data):I.isCompressedTexture?R.compressedTexSubImage2D(R.TEXTURE_2D,B,S.x,S.y,I.mipmaps[0].width,I.mipmaps[0].height,Et,I.mipmaps[0].data):R.texSubImage2D(R.TEXTURE_2D,B,S.x,S.y,Et,Rt,I.image),B===0&&O.generateMipmaps&&R.generateMipmap(R.TEXTURE_2D),$.unbindTexture()},this.copyTextureToTexture3D=function(S,I,O,B,N=0){if(g.isWebGL1Renderer){console.warn("THREE.WebGLRenderer.copyTextureToTexture3D: can only be used with WebGL2.");return}const mt=Math.round(S.max.x-S.min.x),Et=Math.round(S.max.y-S.min.y),Rt=S.max.z-S.min.z+1,Ct=bt.convert(B.format),Ht=bt.convert(B.type);let Ut;if(B.isData3DTexture)xt.setTexture3D(B,0),Ut=R.TEXTURE_3D;else if(B.isDataArrayTexture||B.isCompressedArrayTexture)xt.setTexture2DArray(B,0),Ut=R.TEXTURE_2D_ARRAY;else{console.warn("THREE.WebGLRenderer.copyTextureToTexture3D: only supports THREE.DataTexture3D and THREE.DataTexture2DArray.");return}R.pixelStorei(R.UNPACK_FLIP_Y_WEBGL,B.flipY),R.pixelStorei(R.UNPACK_PREMULTIPLY_ALPHA_WEBGL,B.premultiplyAlpha),R.pixelStorei(R.UNPACK_ALIGNMENT,B.unpackAlignment);const Nt=R.getParameter(R.UNPACK_ROW_LENGTH),ie=R.getParameter(R.UNPACK_IMAGE_HEIGHT),Te=R.getParameter(R.UNPACK_SKIP_PIXELS),ce=R.getParameter(R.UNPACK_SKIP_ROWS),Xe=R.getParameter(R.UNPACK_SKIP_IMAGES),ee=O.isCompressedTexture?O.mipmaps[N]:O.image;R.pixelStorei(R.UNPACK_ROW_LENGTH,ee.width),R.pixelStorei(R.UNPACK_IMAGE_HEIGHT,ee.height),R.pixelStorei(R.UNPACK_SKIP_PIXELS,S.min.x),R.pixelStorei(R.UNPACK_SKIP_ROWS,S.min.y),R.pixelStorei(R.UNPACK_SKIP_IMAGES,S.min.z),O.isDataTexture||O.isData3DTexture?R.texSubImage3D(Ut,N,I.x,I.y,I.z,mt,Et,Rt,Ct,Ht,ee.data):B.isCompressedArrayTexture?R.compressedTexSubImage3D(Ut,N,I.x,I.y,I.z,mt,Et,Rt,Ct,ee.data):R.texSubImage3D(Ut,N,I.x,I.y,I.z,mt,Et,Rt,Ct,Ht,ee),R.pixelStorei(R.UNPACK_ROW_LENGTH,Nt),R.pixelStorei(R.UNPACK_IMAGE_HEIGHT,ie),R.pixelStorei(R.UNPACK_SKIP_PIXELS,Te),R.pixelStorei(R.UNPACK_SKIP_ROWS,ce),R.pixelStorei(R.UNPACK_SKIP_IMAGES,Xe),N===0&&B.generateMipmaps&&R.generateMipmap(Ut),$.unbindTexture()},this.initTexture=function(S){S.isCubeTexture?xt.setTextureCube(S,0):S.isData3DTexture?xt.setTexture3D(S,0):S.isDataArrayTexture||S.isCompressedArrayTexture?xt.setTexture2DArray(S,0):xt.setTexture2D(S,0),$.unbindTexture()},this.resetState=function(){P=0,w=0,b=null,$.reset(),St.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return Qe}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(t){this._outputColorSpace=t;const e=this.getContext();e.drawingBufferColorSpace=t===As?"display-p3":"srgb",e.unpackColorSpace=Yt.workingColorSpace===gr?"display-p3":"srgb"}get useLegacyLights(){return console.warn("THREE.WebGLRenderer: The property .useLegacyLights has been deprecated. Migrate your lighting according to the following guide: https://discourse.threejs.org/t/updates-to-lighting-in-three-js-r155/53733."),this._useLegacyLights}set useLegacyLights(t){console.warn("THREE.WebGLRenderer: The property .useLegacyLights has been deprecated. Migrate your lighting according to the following guide: https://discourse.threejs.org/t/updates-to-lighting-in-three-js-r155/53733."),this._useLegacyLights=t}}class em extends tm{}em.prototype.isWebGL1Renderer=!0;class ol{constructor(t,e=25e-5){this.isFogExp2=!0,this.name="",this.color=new zt(t),this.density=e}clone(){return new ol(this.color,this.density)}toJSON(){return{type:"FogExp2",name:this.name,color:this.color.getHex(),density:this.density}}}class Wm extends ue{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new ke,this.environmentRotation=new ke,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(t,e){return super.copy(t,e),t.background!==null&&(this.background=t.background.clone()),t.environment!==null&&(this.environment=t.environment.clone()),t.fog!==null&&(this.fog=t.fog.clone()),this.backgroundBlurriness=t.backgroundBlurriness,this.backgroundIntensity=t.backgroundIntensity,this.backgroundRotation.copy(t.backgroundRotation),this.environmentRotation.copy(t.environmentRotation),t.overrideMaterial!==null&&(this.overrideMaterial=t.overrideMaterial.clone()),this.matrixAutoUpdate=t.matrixAutoUpdate,this}toJSON(t){const e=super.toJSON(t);return this.fog!==null&&(e.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(e.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(e.object.backgroundIntensity=this.backgroundIntensity),e.object.backgroundRotation=this.backgroundRotation.toArray(),e.object.environmentRotation=this.environmentRotation.toArray(),e}}class nm extends ve{constructor(t=null,e=1,n=1,r,s,o,a,l,c=de,h=de,u,d){super(null,o,a,l,c,h,r,s,u,d),this.isDataTexture=!0,this.image={data:t,width:e,height:n},this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class co extends Le{constructor(t,e,n,r=1){super(t,e,n),this.isInstancedBufferAttribute=!0,this.meshPerAttribute=r}copy(t){return super.copy(t),this.meshPerAttribute=t.meshPerAttribute,this}toJSON(){const t=super.toJSON();return t.meshPerAttribute=this.meshPerAttribute,t.isInstancedBufferAttribute=!0,t}}const $n=new Jt,ho=new Jt,nr=[],uo=new In,im=new Jt,vi=new Oe,xi=new ci;class Xm extends Oe{constructor(t,e,n){super(t,e),this.isInstancedMesh=!0,this.instanceMatrix=new co(new Float32Array(n*16),16),this.instanceColor=null,this.morphTexture=null,this.count=n,this.boundingBox=null,this.boundingSphere=null;for(let r=0;r<n;r++)this.setMatrixAt(r,im)}computeBoundingBox(){const t=this.geometry,e=this.count;this.boundingBox===null&&(this.boundingBox=new In),t.boundingBox===null&&t.computeBoundingBox(),this.boundingBox.makeEmpty();for(let n=0;n<e;n++)this.getMatrixAt(n,$n),uo.copy(t.boundingBox).applyMatrix4($n),this.boundingBox.union(uo)}computeBoundingSphere(){const t=this.geometry,e=this.count;this.boundingSphere===null&&(this.boundingSphere=new ci),t.boundingSphere===null&&t.computeBoundingSphere(),this.boundingSphere.makeEmpty();for(let n=0;n<e;n++)this.getMatrixAt(n,$n),xi.copy(t.boundingSphere).applyMatrix4($n),this.boundingSphere.union(xi)}copy(t,e){return super.copy(t,e),this.instanceMatrix.copy(t.instanceMatrix),t.instanceColor!==null&&(this.instanceColor=t.instanceColor.clone()),this.count=t.count,t.boundingBox!==null&&(this.boundingBox=t.boundingBox.clone()),t.boundingSphere!==null&&(this.boundingSphere=t.boundingSphere.clone()),this}getColorAt(t,e){e.fromArray(this.instanceColor.array,t*3)}getMatrixAt(t,e){e.fromArray(this.instanceMatrix.array,t*16)}getMorphAt(t,e){const n=e.morphTargetInfluences,r=this.morphTexture.source.data.data,s=n.length+1,o=t*s+1;for(let a=0;a<n.length;a++)n[a]=r[o+a]}raycast(t,e){const n=this.matrixWorld,r=this.count;if(vi.geometry=this.geometry,vi.material=this.material,vi.material!==void 0&&(this.boundingSphere===null&&this.computeBoundingSphere(),xi.copy(this.boundingSphere),xi.applyMatrix4(n),t.ray.intersectsSphere(xi)!==!1))for(let s=0;s<r;s++){this.getMatrixAt(s,$n),ho.multiplyMatrices(n,$n),vi.matrixWorld=ho,vi.raycast(t,nr);for(let o=0,a=nr.length;o<a;o++){const l=nr[o];l.instanceId=s,l.object=this,e.push(l)}nr.length=0}}setColorAt(t,e){this.instanceColor===null&&(this.instanceColor=new co(new Float32Array(this.instanceMatrix.count*3),3)),e.toArray(this.instanceColor.array,t*3)}setMatrixAt(t,e){e.toArray(this.instanceMatrix.array,t*16)}setMorphAt(t,e){const n=e.morphTargetInfluences,r=n.length+1;this.morphTexture===null&&(this.morphTexture=new nm(new Float32Array(r*this.count),r,this.count,No,He));const s=this.morphTexture.source.data.data;let o=0;for(let c=0;c<n.length;c++)o+=n[c];const a=this.geometry.morphTargetsRelative?1:1-o,l=r*t;s[l]=a,s.set(n,l+1)}updateMorphTargets(){}dispose(){this.dispatchEvent({type:"dispose"})}}class xr extends hi{constructor(t){super(),this.isLineBasicMaterial=!0,this.type="LineBasicMaterial",this.color=new zt(16777215),this.map=null,this.linewidth=1,this.linecap="round",this.linejoin="round",this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.linewidth=t.linewidth,this.linecap=t.linecap,this.linejoin=t.linejoin,this.fog=t.fog,this}}const fo=new C,po=new C,mo=new Jt,rs=new ws,ir=new ci;class rm extends ue{constructor(t=new pe,e=new xr){super(),this.isLine=!0,this.type="Line",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}computeLineDistances(){const t=this.geometry;if(t.index===null){const e=t.attributes.position,n=[0];for(let r=1,s=e.count;r<s;r++)fo.fromBufferAttribute(e,r-1),po.fromBufferAttribute(e,r),n[r]=n[r-1],n[r]+=fo.distanceTo(po);t.setAttribute("lineDistance",new qt(n,1))}else console.warn("THREE.Line.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}raycast(t,e){const n=this.geometry,r=this.matrixWorld,s=t.params.Line.threshold,o=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),ir.copy(n.boundingSphere),ir.applyMatrix4(r),ir.radius+=s,t.ray.intersectsSphere(ir)===!1)return;mo.copy(r).invert(),rs.copy(t.ray).applyMatrix4(mo);const a=s/((this.scale.x+this.scale.y+this.scale.z)/3),l=a*a,c=new C,h=new C,u=new C,d=new C,m=this.isLineSegments?2:1,_=n.index,p=n.attributes.position;if(_!==null){const f=Math.max(0,o.start),y=Math.min(_.count,o.start+o.count);for(let g=f,E=y-1;g<E;g+=m){const P=_.getX(g),w=_.getX(g+1);if(c.fromBufferAttribute(p,P),h.fromBufferAttribute(p,w),rs.distanceSqToSegment(c,h,d,u)>l)continue;d.applyMatrix4(this.matrixWorld);const U=t.ray.origin.distanceTo(d);U<t.near||U>t.far||e.push({distance:U,point:u.clone().applyMatrix4(this.matrixWorld),index:g,face:null,faceIndex:null,object:this})}}else{const f=Math.max(0,o.start),y=Math.min(p.count,o.start+o.count);for(let g=f,E=y-1;g<E;g+=m){if(c.fromBufferAttribute(p,g),h.fromBufferAttribute(p,g+1),rs.distanceSqToSegment(c,h,d,u)>l)continue;d.applyMatrix4(this.matrixWorld);const w=t.ray.origin.distanceTo(d);w<t.near||w>t.far||e.push({distance:w,point:u.clone().applyMatrix4(this.matrixWorld),index:g,face:null,faceIndex:null,object:this})}}}updateMorphTargets(){const e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){const r=e[n[0]];if(r!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let s=0,o=r.length;s<o;s++){const a=r[s].name||String(s);this.morphTargetInfluences.push(0),this.morphTargetDictionary[a]=s}}}}}const go=new C,_o=new C;class Ls extends rm{constructor(t,e){super(t,e),this.isLineSegments=!0,this.type="LineSegments"}computeLineDistances(){const t=this.geometry;if(t.index===null){const e=t.attributes.position,n=[];for(let r=0,s=e.count;r<s;r+=2)go.fromBufferAttribute(e,r),_o.fromBufferAttribute(e,r+1),n[r]=r===0?0:n[r-1],n[r+1]=n[r]+go.distanceTo(_o);t.setAttribute("lineDistance",new qt(n,1))}else console.warn("THREE.LineSegments.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}}class qm extends ve{constructor(t,e,n,r,s,o,a,l,c){super(t,e,n,r,s,o,a,l,c),this.isCanvasTexture=!0,this.needsUpdate=!0}}class We{constructor(){this.type="Curve",this.arcLengthDivisions=200}getPoint(){return console.warn("THREE.Curve: .getPoint() not implemented."),null}getPointAt(t,e){const n=this.getUtoTmapping(t);return this.getPoint(n,e)}getPoints(t=5){const e=[];for(let n=0;n<=t;n++)e.push(this.getPoint(n/t));return e}getSpacedPoints(t=5){const e=[];for(let n=0;n<=t;n++)e.push(this.getPointAt(n/t));return e}getLength(){const t=this.getLengths();return t[t.length-1]}getLengths(t=this.arcLengthDivisions){if(this.cacheArcLengths&&this.cacheArcLengths.length===t+1&&!this.needsUpdate)return this.cacheArcLengths;this.needsUpdate=!1;const e=[];let n,r=this.getPoint(0),s=0;e.push(0);for(let o=1;o<=t;o++)n=this.getPoint(o/t),s+=n.distanceTo(r),e.push(s),r=n;return this.cacheArcLengths=e,e}updateArcLengths(){this.needsUpdate=!0,this.getLengths()}getUtoTmapping(t,e){const n=this.getLengths();let r=0;const s=n.length;let o;e?o=e:o=t*n[s-1];let a=0,l=s-1,c;for(;a<=l;)if(r=Math.floor(a+(l-a)/2),c=n[r]-o,c<0)a=r+1;else if(c>0)l=r-1;else{l=r;break}if(r=l,n[r]===o)return r/(s-1);const h=n[r],d=n[r+1]-h,m=(o-h)/d;return(r+m)/(s-1)}getTangent(t,e){let r=t-1e-4,s=t+1e-4;r<0&&(r=0),s>1&&(s=1);const o=this.getPoint(r),a=this.getPoint(s),l=e||(o.isVector2?new it:new C);return l.copy(a).sub(o).normalize(),l}getTangentAt(t,e){const n=this.getUtoTmapping(t);return this.getTangent(n,e)}computeFrenetFrames(t,e){const n=new C,r=[],s=[],o=[],a=new C,l=new Jt;for(let m=0;m<=t;m++){const _=m/t;r[m]=this.getTangentAt(_,new C)}s[0]=new C,o[0]=new C;let c=Number.MAX_VALUE;const h=Math.abs(r[0].x),u=Math.abs(r[0].y),d=Math.abs(r[0].z);h<=c&&(c=h,n.set(1,0,0)),u<=c&&(c=u,n.set(0,1,0)),d<=c&&n.set(0,0,1),a.crossVectors(r[0],n).normalize(),s[0].crossVectors(r[0],a),o[0].crossVectors(r[0],s[0]);for(let m=1;m<=t;m++){if(s[m]=s[m-1].clone(),o[m]=o[m-1].clone(),a.crossVectors(r[m-1],r[m]),a.length()>Number.EPSILON){a.normalize();const _=Math.acos(ae(r[m-1].dot(r[m]),-1,1));s[m].applyMatrix4(l.makeRotationAxis(a,_))}o[m].crossVectors(r[m],s[m])}if(e===!0){let m=Math.acos(ae(s[0].dot(s[t]),-1,1));m/=t,r[0].dot(a.crossVectors(s[0],s[t]))>0&&(m=-m);for(let _=1;_<=t;_++)s[_].applyMatrix4(l.makeRotationAxis(r[_],m*_)),o[_].crossVectors(r[_],s[_])}return{tangents:r,normals:s,binormals:o}}clone(){return new this.constructor().copy(this)}copy(t){return this.arcLengthDivisions=t.arcLengthDivisions,this}toJSON(){const t={metadata:{version:4.6,type:"Curve",generator:"Curve.toJSON"}};return t.arcLengthDivisions=this.arcLengthDivisions,t.type=this.type,t}fromJSON(t){return this.arcLengthDivisions=t.arcLengthDivisions,this}}class Ds extends We{constructor(t=0,e=0,n=1,r=1,s=0,o=Math.PI*2,a=!1,l=0){super(),this.isEllipseCurve=!0,this.type="EllipseCurve",this.aX=t,this.aY=e,this.xRadius=n,this.yRadius=r,this.aStartAngle=s,this.aEndAngle=o,this.aClockwise=a,this.aRotation=l}getPoint(t,e=new it){const n=e,r=Math.PI*2;let s=this.aEndAngle-this.aStartAngle;const o=Math.abs(s)<Number.EPSILON;for(;s<0;)s+=r;for(;s>r;)s-=r;s<Number.EPSILON&&(o?s=0:s=r),this.aClockwise===!0&&!o&&(s===r?s=-r:s=s-r);const a=this.aStartAngle+t*s;let l=this.aX+this.xRadius*Math.cos(a),c=this.aY+this.yRadius*Math.sin(a);if(this.aRotation!==0){const h=Math.cos(this.aRotation),u=Math.sin(this.aRotation),d=l-this.aX,m=c-this.aY;l=d*h-m*u+this.aX,c=d*u+m*h+this.aY}return n.set(l,c)}copy(t){return super.copy(t),this.aX=t.aX,this.aY=t.aY,this.xRadius=t.xRadius,this.yRadius=t.yRadius,this.aStartAngle=t.aStartAngle,this.aEndAngle=t.aEndAngle,this.aClockwise=t.aClockwise,this.aRotation=t.aRotation,this}toJSON(){const t=super.toJSON();return t.aX=this.aX,t.aY=this.aY,t.xRadius=this.xRadius,t.yRadius=this.yRadius,t.aStartAngle=this.aStartAngle,t.aEndAngle=this.aEndAngle,t.aClockwise=this.aClockwise,t.aRotation=this.aRotation,t}fromJSON(t){return super.fromJSON(t),this.aX=t.aX,this.aY=t.aY,this.xRadius=t.xRadius,this.yRadius=t.yRadius,this.aStartAngle=t.aStartAngle,this.aEndAngle=t.aEndAngle,this.aClockwise=t.aClockwise,this.aRotation=t.aRotation,this}}class sm extends Ds{constructor(t,e,n,r,s,o){super(t,e,n,n,r,s,o),this.isArcCurve=!0,this.type="ArcCurve"}}function Us(){let i=0,t=0,e=0,n=0;function r(s,o,a,l){i=s,t=a,e=-3*s+3*o-2*a-l,n=2*s-2*o+a+l}return{initCatmullRom:function(s,o,a,l,c){r(o,a,c*(a-s),c*(l-o))},initNonuniformCatmullRom:function(s,o,a,l,c,h,u){let d=(o-s)/c-(a-s)/(c+h)+(a-o)/h,m=(a-o)/h-(l-o)/(h+u)+(l-a)/u;d*=h,m*=h,r(o,a,d,m)},calc:function(s){const o=s*s,a=o*s;return i+t*s+e*o+n*a}}}const rr=new C,ss=new Us,as=new Us,os=new Us;class am extends We{constructor(t=[],e=!1,n="centripetal",r=.5){super(),this.isCatmullRomCurve3=!0,this.type="CatmullRomCurve3",this.points=t,this.closed=e,this.curveType=n,this.tension=r}getPoint(t,e=new C){const n=e,r=this.points,s=r.length,o=(s-(this.closed?0:1))*t;let a=Math.floor(o),l=o-a;this.closed?a+=a>0?0:(Math.floor(Math.abs(a)/s)+1)*s:l===0&&a===s-1&&(a=s-2,l=1);let c,h;this.closed||a>0?c=r[(a-1)%s]:(rr.subVectors(r[0],r[1]).add(r[0]),c=rr);const u=r[a%s],d=r[(a+1)%s];if(this.closed||a+2<s?h=r[(a+2)%s]:(rr.subVectors(r[s-1],r[s-2]).add(r[s-1]),h=rr),this.curveType==="centripetal"||this.curveType==="chordal"){const m=this.curveType==="chordal"?.5:.25;let _=Math.pow(c.distanceToSquared(u),m),M=Math.pow(u.distanceToSquared(d),m),p=Math.pow(d.distanceToSquared(h),m);M<1e-4&&(M=1),_<1e-4&&(_=M),p<1e-4&&(p=M),ss.initNonuniformCatmullRom(c.x,u.x,d.x,h.x,_,M,p),as.initNonuniformCatmullRom(c.y,u.y,d.y,h.y,_,M,p),os.initNonuniformCatmullRom(c.z,u.z,d.z,h.z,_,M,p)}else this.curveType==="catmullrom"&&(ss.initCatmullRom(c.x,u.x,d.x,h.x,this.tension),as.initCatmullRom(c.y,u.y,d.y,h.y,this.tension),os.initCatmullRom(c.z,u.z,d.z,h.z,this.tension));return n.set(ss.calc(l),as.calc(l),os.calc(l)),n}copy(t){super.copy(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const r=t.points[e];this.points.push(r.clone())}return this.closed=t.closed,this.curveType=t.curveType,this.tension=t.tension,this}toJSON(){const t=super.toJSON();t.points=[];for(let e=0,n=this.points.length;e<n;e++){const r=this.points[e];t.points.push(r.toArray())}return t.closed=this.closed,t.curveType=this.curveType,t.tension=this.tension,t}fromJSON(t){super.fromJSON(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const r=t.points[e];this.points.push(new C().fromArray(r))}return this.closed=t.closed,this.curveType=t.curveType,this.tension=t.tension,this}}function vo(i,t,e,n,r){const s=(n-t)*.5,o=(r-e)*.5,a=i*i,l=i*a;return(2*e-2*n+s+o)*l+(-3*e+3*n-2*s-o)*a+s*i+e}function om(i,t){const e=1-i;return e*e*t}function lm(i,t){return 2*(1-i)*i*t}function cm(i,t){return i*i*t}function Ei(i,t,e,n){return om(i,t)+lm(i,e)+cm(i,n)}function hm(i,t){const e=1-i;return e*e*e*t}function um(i,t){const e=1-i;return 3*e*e*i*t}function fm(i,t){return 3*(1-i)*i*i*t}function dm(i,t){return i*i*i*t}function Ti(i,t,e,n,r){return hm(i,t)+um(i,e)+fm(i,n)+dm(i,r)}class ll extends We{constructor(t=new it,e=new it,n=new it,r=new it){super(),this.isCubicBezierCurve=!0,this.type="CubicBezierCurve",this.v0=t,this.v1=e,this.v2=n,this.v3=r}getPoint(t,e=new it){const n=e,r=this.v0,s=this.v1,o=this.v2,a=this.v3;return n.set(Ti(t,r.x,s.x,o.x,a.x),Ti(t,r.y,s.y,o.y,a.y)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this.v3.copy(t.v3),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t.v3=this.v3.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this.v3.fromArray(t.v3),this}}class pm extends We{constructor(t=new C,e=new C,n=new C,r=new C){super(),this.isCubicBezierCurve3=!0,this.type="CubicBezierCurve3",this.v0=t,this.v1=e,this.v2=n,this.v3=r}getPoint(t,e=new C){const n=e,r=this.v0,s=this.v1,o=this.v2,a=this.v3;return n.set(Ti(t,r.x,s.x,o.x,a.x),Ti(t,r.y,s.y,o.y,a.y),Ti(t,r.z,s.z,o.z,a.z)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this.v3.copy(t.v3),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t.v3=this.v3.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this.v3.fromArray(t.v3),this}}class cl extends We{constructor(t=new it,e=new it){super(),this.isLineCurve=!0,this.type="LineCurve",this.v1=t,this.v2=e}getPoint(t,e=new it){const n=e;return t===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(t).add(this.v1)),n}getPointAt(t,e){return this.getPoint(t,e)}getTangent(t,e=new it){return e.subVectors(this.v2,this.v1).normalize()}getTangentAt(t,e){return this.getTangent(t,e)}copy(t){return super.copy(t),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class mm extends We{constructor(t=new C,e=new C){super(),this.isLineCurve3=!0,this.type="LineCurve3",this.v1=t,this.v2=e}getPoint(t,e=new C){const n=e;return t===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(t).add(this.v1)),n}getPointAt(t,e){return this.getPoint(t,e)}getTangent(t,e=new C){return e.subVectors(this.v2,this.v1).normalize()}getTangentAt(t,e){return this.getTangent(t,e)}copy(t){return super.copy(t),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class hl extends We{constructor(t=new it,e=new it,n=new it){super(),this.isQuadraticBezierCurve=!0,this.type="QuadraticBezierCurve",this.v0=t,this.v1=e,this.v2=n}getPoint(t,e=new it){const n=e,r=this.v0,s=this.v1,o=this.v2;return n.set(Ei(t,r.x,s.x,o.x),Ei(t,r.y,s.y,o.y)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class gm extends We{constructor(t=new C,e=new C,n=new C){super(),this.isQuadraticBezierCurve3=!0,this.type="QuadraticBezierCurve3",this.v0=t,this.v1=e,this.v2=n}getPoint(t,e=new C){const n=e,r=this.v0,s=this.v1,o=this.v2;return n.set(Ei(t,r.x,s.x,o.x),Ei(t,r.y,s.y,o.y),Ei(t,r.z,s.z,o.z)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class ul extends We{constructor(t=[]){super(),this.isSplineCurve=!0,this.type="SplineCurve",this.points=t}getPoint(t,e=new it){const n=e,r=this.points,s=(r.length-1)*t,o=Math.floor(s),a=s-o,l=r[o===0?o:o-1],c=r[o],h=r[o>r.length-2?r.length-1:o+1],u=r[o>r.length-3?r.length-1:o+2];return n.set(vo(a,l.x,c.x,h.x,u.x),vo(a,l.y,c.y,h.y,u.y)),n}copy(t){super.copy(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const r=t.points[e];this.points.push(r.clone())}return this}toJSON(){const t=super.toJSON();t.points=[];for(let e=0,n=this.points.length;e<n;e++){const r=this.points[e];t.points.push(r.toArray())}return t}fromJSON(t){super.fromJSON(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const r=t.points[e];this.points.push(new it().fromArray(r))}return this}}var xs=Object.freeze({__proto__:null,ArcCurve:sm,CatmullRomCurve3:am,CubicBezierCurve:ll,CubicBezierCurve3:pm,EllipseCurve:Ds,LineCurve:cl,LineCurve3:mm,QuadraticBezierCurve:hl,QuadraticBezierCurve3:gm,SplineCurve:ul});class _m extends We{constructor(){super(),this.type="CurvePath",this.curves=[],this.autoClose=!1}add(t){this.curves.push(t)}closePath(){const t=this.curves[0].getPoint(0),e=this.curves[this.curves.length-1].getPoint(1);if(!t.equals(e)){const n=t.isVector2===!0?"LineCurve":"LineCurve3";this.curves.push(new xs[n](e,t))}return this}getPoint(t,e){const n=t*this.getLength(),r=this.getCurveLengths();let s=0;for(;s<r.length;){if(r[s]>=n){const o=r[s]-n,a=this.curves[s],l=a.getLength(),c=l===0?0:1-o/l;return a.getPointAt(c,e)}s++}return null}getLength(){const t=this.getCurveLengths();return t[t.length-1]}updateArcLengths(){this.needsUpdate=!0,this.cacheLengths=null,this.getCurveLengths()}getCurveLengths(){if(this.cacheLengths&&this.cacheLengths.length===this.curves.length)return this.cacheLengths;const t=[];let e=0;for(let n=0,r=this.curves.length;n<r;n++)e+=this.curves[n].getLength(),t.push(e);return this.cacheLengths=t,t}getSpacedPoints(t=40){const e=[];for(let n=0;n<=t;n++)e.push(this.getPoint(n/t));return this.autoClose&&e.push(e[0]),e}getPoints(t=12){const e=[];let n;for(let r=0,s=this.curves;r<s.length;r++){const o=s[r],a=o.isEllipseCurve?t*2:o.isLineCurve||o.isLineCurve3?1:o.isSplineCurve?t*o.points.length:t,l=o.getPoints(a);for(let c=0;c<l.length;c++){const h=l[c];n&&n.equals(h)||(e.push(h),n=h)}}return this.autoClose&&e.length>1&&!e[e.length-1].equals(e[0])&&e.push(e[0]),e}copy(t){super.copy(t),this.curves=[];for(let e=0,n=t.curves.length;e<n;e++){const r=t.curves[e];this.curves.push(r.clone())}return this.autoClose=t.autoClose,this}toJSON(){const t=super.toJSON();t.autoClose=this.autoClose,t.curves=[];for(let e=0,n=this.curves.length;e<n;e++){const r=this.curves[e];t.curves.push(r.toJSON())}return t}fromJSON(t){super.fromJSON(t),this.autoClose=t.autoClose,this.curves=[];for(let e=0,n=t.curves.length;e<n;e++){const r=t.curves[e];this.curves.push(new xs[r.type]().fromJSON(r))}return this}}class xo extends _m{constructor(t){super(),this.type="Path",this.currentPoint=new it,t&&this.setFromPoints(t)}setFromPoints(t){this.moveTo(t[0].x,t[0].y);for(let e=1,n=t.length;e<n;e++)this.lineTo(t[e].x,t[e].y);return this}moveTo(t,e){return this.currentPoint.set(t,e),this}lineTo(t,e){const n=new cl(this.currentPoint.clone(),new it(t,e));return this.curves.push(n),this.currentPoint.set(t,e),this}quadraticCurveTo(t,e,n,r){const s=new hl(this.currentPoint.clone(),new it(t,e),new it(n,r));return this.curves.push(s),this.currentPoint.set(n,r),this}bezierCurveTo(t,e,n,r,s,o){const a=new ll(this.currentPoint.clone(),new it(t,e),new it(n,r),new it(s,o));return this.curves.push(a),this.currentPoint.set(s,o),this}splineThru(t){const e=[this.currentPoint.clone()].concat(t),n=new ul(e);return this.curves.push(n),this.currentPoint.copy(t[t.length-1]),this}arc(t,e,n,r,s,o){const a=this.currentPoint.x,l=this.currentPoint.y;return this.absarc(t+a,e+l,n,r,s,o),this}absarc(t,e,n,r,s,o){return this.absellipse(t,e,n,n,r,s,o),this}ellipse(t,e,n,r,s,o,a,l){const c=this.currentPoint.x,h=this.currentPoint.y;return this.absellipse(t+c,e+h,n,r,s,o,a,l),this}absellipse(t,e,n,r,s,o,a,l){const c=new Ds(t,e,n,r,s,o,a,l);if(this.curves.length>0){const u=c.getPoint(0);u.equals(this.currentPoint)||this.lineTo(u.x,u.y)}this.curves.push(c);const h=c.getPoint(1);return this.currentPoint.copy(h),this}copy(t){return super.copy(t),this.currentPoint.copy(t.currentPoint),this}toJSON(){const t=super.toJSON();return t.currentPoint=this.currentPoint.toArray(),t}fromJSON(t){return super.fromJSON(t),this.currentPoint.fromArray(t.currentPoint),this}}class fl extends pe{constructor(t=1,e=32,n=0,r=Math.PI*2){super(),this.type="CircleGeometry",this.parameters={radius:t,segments:e,thetaStart:n,thetaLength:r},e=Math.max(3,e);const s=[],o=[],a=[],l=[],c=new C,h=new it;o.push(0,0,0),a.push(0,0,1),l.push(.5,.5);for(let u=0,d=3;u<=e;u++,d+=3){const m=n+u/e*r;c.x=t*Math.cos(m),c.y=t*Math.sin(m),o.push(c.x,c.y,c.z),a.push(0,0,1),h.x=(o[d]/t+1)/2,h.y=(o[d+1]/t+1)/2,l.push(h.x,h.y)}for(let u=1;u<=e;u++)s.push(u,u+1,0);this.setIndex(s),this.setAttribute("position",new qt(o,3)),this.setAttribute("normal",new qt(a,3)),this.setAttribute("uv",new qt(l,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new fl(t.radius,t.segments,t.thetaStart,t.thetaLength)}}class Is extends pe{constructor(t=1,e=1,n=1,r=32,s=1,o=!1,a=0,l=Math.PI*2){super(),this.type="CylinderGeometry",this.parameters={radiusTop:t,radiusBottom:e,height:n,radialSegments:r,heightSegments:s,openEnded:o,thetaStart:a,thetaLength:l};const c=this;r=Math.floor(r),s=Math.floor(s);const h=[],u=[],d=[],m=[];let _=0;const M=[],p=n/2;let f=0;y(),o===!1&&(t>0&&g(!0),e>0&&g(!1)),this.setIndex(h),this.setAttribute("position",new qt(u,3)),this.setAttribute("normal",new qt(d,3)),this.setAttribute("uv",new qt(m,2));function y(){const E=new C,P=new C;let w=0;const b=(e-t)/n;for(let U=0;U<=s;U++){const V=[],v=U/s,A=v*(e-t)+t;for(let Z=0;Z<=r;Z++){const K=Z/r,L=K*l+a,k=Math.sin(L),z=Math.cos(L);P.x=A*k,P.y=-v*n+p,P.z=A*z,u.push(P.x,P.y,P.z),E.set(k,b,z).normalize(),d.push(E.x,E.y,E.z),m.push(K,1-v),V.push(_++)}M.push(V)}for(let U=0;U<r;U++)for(let V=0;V<s;V++){const v=M[V][U],A=M[V+1][U],Z=M[V+1][U+1],K=M[V][U+1];h.push(v,A,K),h.push(A,Z,K),w+=6}c.addGroup(f,w,0),f+=w}function g(E){const P=_,w=new it,b=new C;let U=0;const V=E===!0?t:e,v=E===!0?1:-1;for(let Z=1;Z<=r;Z++)u.push(0,p*v,0),d.push(0,v,0),m.push(.5,.5),_++;const A=_;for(let Z=0;Z<=r;Z++){const L=Z/r*l+a,k=Math.cos(L),z=Math.sin(L);b.x=V*z,b.y=p*v,b.z=V*k,u.push(b.x,b.y,b.z),d.push(0,v,0),w.x=k*.5+.5,w.y=z*.5*v+.5,m.push(w.x,w.y),_++}for(let Z=0;Z<r;Z++){const K=P+Z,L=A+Z;E===!0?h.push(L,L+1,K):h.push(L+1,L,K),U+=3}c.addGroup(f,U,E===!0?1:2),f+=U}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Is(t.radiusTop,t.radiusBottom,t.height,t.radialSegments,t.heightSegments,t.openEnded,t.thetaStart,t.thetaLength)}}class dl extends Is{constructor(t=1,e=1,n=32,r=1,s=!1,o=0,a=Math.PI*2){super(0,t,e,n,r,s,o,a),this.type="ConeGeometry",this.parameters={radius:t,height:e,radialSegments:n,heightSegments:r,openEnded:s,thetaStart:o,thetaLength:a}}static fromJSON(t){return new dl(t.radius,t.height,t.radialSegments,t.heightSegments,t.openEnded,t.thetaStart,t.thetaLength)}}class Mr extends pe{constructor(t=[],e=[],n=1,r=0){super(),this.type="PolyhedronGeometry",this.parameters={vertices:t,indices:e,radius:n,detail:r};const s=[],o=[];a(r),c(n),h(),this.setAttribute("position",new qt(s,3)),this.setAttribute("normal",new qt(s.slice(),3)),this.setAttribute("uv",new qt(o,2)),r===0?this.computeVertexNormals():this.normalizeNormals();function a(y){const g=new C,E=new C,P=new C;for(let w=0;w<e.length;w+=3)m(e[w+0],g),m(e[w+1],E),m(e[w+2],P),l(g,E,P,y)}function l(y,g,E,P){const w=P+1,b=[];for(let U=0;U<=w;U++){b[U]=[];const V=y.clone().lerp(E,U/w),v=g.clone().lerp(E,U/w),A=w-U;for(let Z=0;Z<=A;Z++)Z===0&&U===w?b[U][Z]=V:b[U][Z]=V.clone().lerp(v,Z/A)}for(let U=0;U<w;U++)for(let V=0;V<2*(w-U)-1;V++){const v=Math.floor(V/2);V%2===0?(d(b[U][v+1]),d(b[U+1][v]),d(b[U][v])):(d(b[U][v+1]),d(b[U+1][v+1]),d(b[U+1][v]))}}function c(y){const g=new C;for(let E=0;E<s.length;E+=3)g.x=s[E+0],g.y=s[E+1],g.z=s[E+2],g.normalize().multiplyScalar(y),s[E+0]=g.x,s[E+1]=g.y,s[E+2]=g.z}function h(){const y=new C;for(let g=0;g<s.length;g+=3){y.x=s[g+0],y.y=s[g+1],y.z=s[g+2];const E=p(y)/2/Math.PI+.5,P=f(y)/Math.PI+.5;o.push(E,1-P)}_(),u()}function u(){for(let y=0;y<o.length;y+=6){const g=o[y+0],E=o[y+2],P=o[y+4],w=Math.max(g,E,P),b=Math.min(g,E,P);w>.9&&b<.1&&(g<.2&&(o[y+0]+=1),E<.2&&(o[y+2]+=1),P<.2&&(o[y+4]+=1))}}function d(y){s.push(y.x,y.y,y.z)}function m(y,g){const E=y*3;g.x=t[E+0],g.y=t[E+1],g.z=t[E+2]}function _(){const y=new C,g=new C,E=new C,P=new C,w=new it,b=new it,U=new it;for(let V=0,v=0;V<s.length;V+=9,v+=6){y.set(s[V+0],s[V+1],s[V+2]),g.set(s[V+3],s[V+4],s[V+5]),E.set(s[V+6],s[V+7],s[V+8]),w.set(o[v+0],o[v+1]),b.set(o[v+2],o[v+3]),U.set(o[v+4],o[v+5]),P.copy(y).add(g).add(E).divideScalar(3);const A=p(P);M(w,v+0,y,A),M(b,v+2,g,A),M(U,v+4,E,A)}}function M(y,g,E,P){P<0&&y.x===1&&(o[g]=y.x-1),E.x===0&&E.z===0&&(o[g]=P/2/Math.PI+.5)}function p(y){return Math.atan2(y.z,-y.x)}function f(y){return Math.atan2(-y.y,Math.sqrt(y.x*y.x+y.z*y.z))}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Mr(t.vertices,t.indices,t.radius,t.details)}}class pl extends Mr{constructor(t=1,e=0){const n=(1+Math.sqrt(5))/2,r=1/n,s=[-1,-1,-1,-1,-1,1,-1,1,-1,-1,1,1,1,-1,-1,1,-1,1,1,1,-1,1,1,1,0,-r,-n,0,-r,n,0,r,-n,0,r,n,-r,-n,0,-r,n,0,r,-n,0,r,n,0,-n,0,-r,n,0,-r,-n,0,r,n,0,r],o=[3,11,7,3,7,15,3,15,13,7,19,17,7,17,6,7,6,15,17,4,8,17,8,10,17,10,6,8,0,16,8,16,2,8,2,10,0,12,1,0,1,18,0,18,16,6,10,2,6,2,13,6,13,15,2,16,18,2,18,3,2,3,13,18,1,9,18,9,11,18,11,3,4,14,12,4,12,0,4,0,8,11,9,5,11,5,19,11,19,7,19,5,14,19,14,4,19,4,17,1,12,14,1,14,5,1,5,9];super(s,o,t,e),this.type="DodecahedronGeometry",this.parameters={radius:t,detail:e}}static fromJSON(t){return new pl(t.radius,t.detail)}}class ml extends xo{constructor(t){super(t),this.uuid=Un(),this.type="Shape",this.holes=[]}getPointsHoles(t){const e=[];for(let n=0,r=this.holes.length;n<r;n++)e[n]=this.holes[n].getPoints(t);return e}extractPoints(t){return{shape:this.getPoints(t),holes:this.getPointsHoles(t)}}copy(t){super.copy(t),this.holes=[];for(let e=0,n=t.holes.length;e<n;e++){const r=t.holes[e];this.holes.push(r.clone())}return this}toJSON(){const t=super.toJSON();t.uuid=this.uuid,t.holes=[];for(let e=0,n=this.holes.length;e<n;e++){const r=this.holes[e];t.holes.push(r.toJSON())}return t}fromJSON(t){super.fromJSON(t),this.uuid=t.uuid,this.holes=[];for(let e=0,n=t.holes.length;e<n;e++){const r=t.holes[e];this.holes.push(new xo().fromJSON(r))}return this}}const vm={triangulate:function(i,t,e=2){const n=t&&t.length,r=n?t[0]*e:i.length;let s=gl(i,0,r,e,!0);const o=[];if(!s||s.next===s.prev)return o;let a,l,c,h,u,d,m;if(n&&(s=Em(i,t,s,e)),i.length>80*e){a=c=i[0],l=h=i[1];for(let _=e;_<r;_+=e)u=i[_],d=i[_+1],u<a&&(a=u),d<l&&(l=d),u>c&&(c=u),d>h&&(h=d);m=Math.max(c-a,h-l),m=m!==0?32767/m:0}return wi(s,o,e,a,l,m,0),o}};function gl(i,t,e,n,r){let s,o;if(r===Im(i,t,e,n)>0)for(s=t;s<e;s+=n)o=Mo(s,i[s],i[s+1],o);else for(s=e-n;s>=t;s-=n)o=Mo(s,i[s],i[s+1],o);return o&&Sr(o,o.next)&&(Ci(o),o=o.next),o}function Dn(i,t){if(!i)return i;t||(t=i);let e=i,n;do if(n=!1,!e.steiner&&(Sr(e,e.next)||ne(e.prev,e,e.next)===0)){if(Ci(e),e=t=e.prev,e===e.next)break;n=!0}else e=e.next;while(n||e!==t);return t}function wi(i,t,e,n,r,s,o){if(!i)return;!o&&s&&Rm(i,n,r,s);let a=i,l,c;for(;i.prev!==i.next;){if(l=i.prev,c=i.next,s?Mm(i,n,r,s):xm(i)){t.push(l.i/e|0),t.push(i.i/e|0),t.push(c.i/e|0),Ci(i),i=c.next,a=c.next;continue}if(i=c,i===a){o?o===1?(i=Sm(Dn(i),t,e),wi(i,t,e,n,r,s,2)):o===2&&ym(i,t,e,n,r,s):wi(Dn(i),t,e,n,r,s,1);break}}}function xm(i){const t=i.prev,e=i,n=i.next;if(ne(t,e,n)>=0)return!1;const r=t.x,s=e.x,o=n.x,a=t.y,l=e.y,c=n.y,h=r<s?r<o?r:o:s<o?s:o,u=a<l?a<c?a:c:l<c?l:c,d=r>s?r>o?r:o:s>o?s:o,m=a>l?a>c?a:c:l>c?l:c;let _=n.next;for(;_!==t;){if(_.x>=h&&_.x<=d&&_.y>=u&&_.y<=m&&ei(r,a,s,l,o,c,_.x,_.y)&&ne(_.prev,_,_.next)>=0)return!1;_=_.next}return!0}function Mm(i,t,e,n){const r=i.prev,s=i,o=i.next;if(ne(r,s,o)>=0)return!1;const a=r.x,l=s.x,c=o.x,h=r.y,u=s.y,d=o.y,m=a<l?a<c?a:c:l<c?l:c,_=h<u?h<d?h:d:u<d?u:d,M=a>l?a>c?a:c:l>c?l:c,p=h>u?h>d?h:d:u>d?u:d,f=Ms(m,_,t,e,n),y=Ms(M,p,t,e,n);let g=i.prevZ,E=i.nextZ;for(;g&&g.z>=f&&E&&E.z<=y;){if(g.x>=m&&g.x<=M&&g.y>=_&&g.y<=p&&g!==r&&g!==o&&ei(a,h,l,u,c,d,g.x,g.y)&&ne(g.prev,g,g.next)>=0||(g=g.prevZ,E.x>=m&&E.x<=M&&E.y>=_&&E.y<=p&&E!==r&&E!==o&&ei(a,h,l,u,c,d,E.x,E.y)&&ne(E.prev,E,E.next)>=0))return!1;E=E.nextZ}for(;g&&g.z>=f;){if(g.x>=m&&g.x<=M&&g.y>=_&&g.y<=p&&g!==r&&g!==o&&ei(a,h,l,u,c,d,g.x,g.y)&&ne(g.prev,g,g.next)>=0)return!1;g=g.prevZ}for(;E&&E.z<=y;){if(E.x>=m&&E.x<=M&&E.y>=_&&E.y<=p&&E!==r&&E!==o&&ei(a,h,l,u,c,d,E.x,E.y)&&ne(E.prev,E,E.next)>=0)return!1;E=E.nextZ}return!0}function Sm(i,t,e){let n=i;do{const r=n.prev,s=n.next.next;!Sr(r,s)&&_l(r,n,n.next,s)&&Ri(r,s)&&Ri(s,r)&&(t.push(r.i/e|0),t.push(n.i/e|0),t.push(s.i/e|0),Ci(n),Ci(n.next),n=i=s),n=n.next}while(n!==i);return Dn(n)}function ym(i,t,e,n,r,s){let o=i;do{let a=o.next.next;for(;a!==o.prev;){if(o.i!==a.i&&Lm(o,a)){let l=vl(o,a);o=Dn(o,o.next),l=Dn(l,l.next),wi(o,t,e,n,r,s,0),wi(l,t,e,n,r,s,0);return}a=a.next}o=o.next}while(o!==i)}function Em(i,t,e,n){const r=[];let s,o,a,l,c;for(s=0,o=t.length;s<o;s++)a=t[s]*n,l=s<o-1?t[s+1]*n:i.length,c=gl(i,a,l,n,!1),c===c.next&&(c.steiner=!0),r.push(Pm(c));for(r.sort(Tm),s=0;s<r.length;s++)e=Am(r[s],e);return e}function Tm(i,t){return i.x-t.x}function Am(i,t){const e=bm(i,t);if(!e)return t;const n=vl(e,i);return Dn(n,n.next),Dn(e,e.next)}function bm(i,t){let e=t,n=-1/0,r;const s=i.x,o=i.y;do{if(o<=e.y&&o>=e.next.y&&e.next.y!==e.y){const d=e.x+(o-e.y)*(e.next.x-e.x)/(e.next.y-e.y);if(d<=s&&d>n&&(n=d,r=e.x<e.next.x?e:e.next,d===s))return r}e=e.next}while(e!==t);if(!r)return null;const a=r,l=r.x,c=r.y;let h=1/0,u;e=r;do s>=e.x&&e.x>=l&&s!==e.x&&ei(o<c?s:n,o,l,c,o<c?n:s,o,e.x,e.y)&&(u=Math.abs(o-e.y)/(s-e.x),Ri(e,i)&&(u<h||u===h&&(e.x>r.x||e.x===r.x&&wm(r,e)))&&(r=e,h=u)),e=e.next;while(e!==a);return r}function wm(i,t){return ne(i.prev,i,t.prev)<0&&ne(t.next,i,i.next)<0}function Rm(i,t,e,n){let r=i;do r.z===0&&(r.z=Ms(r.x,r.y,t,e,n)),r.prevZ=r.prev,r.nextZ=r.next,r=r.next;while(r!==i);r.prevZ.nextZ=null,r.prevZ=null,Cm(r)}function Cm(i){let t,e,n,r,s,o,a,l,c=1;do{for(e=i,i=null,s=null,o=0;e;){for(o++,n=e,a=0,t=0;t<c&&(a++,n=n.nextZ,!!n);t++);for(l=c;a>0||l>0&&n;)a!==0&&(l===0||!n||e.z<=n.z)?(r=e,e=e.nextZ,a--):(r=n,n=n.nextZ,l--),s?s.nextZ=r:i=r,r.prevZ=s,s=r;e=n}s.nextZ=null,c*=2}while(o>1);return i}function Ms(i,t,e,n,r){return i=(i-e)*r|0,t=(t-n)*r|0,i=(i|i<<8)&16711935,i=(i|i<<4)&252645135,i=(i|i<<2)&858993459,i=(i|i<<1)&1431655765,t=(t|t<<8)&16711935,t=(t|t<<4)&252645135,t=(t|t<<2)&858993459,t=(t|t<<1)&1431655765,i|t<<1}function Pm(i){let t=i,e=i;do(t.x<e.x||t.x===e.x&&t.y<e.y)&&(e=t),t=t.next;while(t!==i);return e}function ei(i,t,e,n,r,s,o,a){return(r-o)*(t-a)>=(i-o)*(s-a)&&(i-o)*(n-a)>=(e-o)*(t-a)&&(e-o)*(s-a)>=(r-o)*(n-a)}function Lm(i,t){return i.next.i!==t.i&&i.prev.i!==t.i&&!Dm(i,t)&&(Ri(i,t)&&Ri(t,i)&&Um(i,t)&&(ne(i.prev,i,t.prev)||ne(i,t.prev,t))||Sr(i,t)&&ne(i.prev,i,i.next)>0&&ne(t.prev,t,t.next)>0)}function ne(i,t,e){return(t.y-i.y)*(e.x-t.x)-(t.x-i.x)*(e.y-t.y)}function Sr(i,t){return i.x===t.x&&i.y===t.y}function _l(i,t,e,n){const r=ar(ne(i,t,e)),s=ar(ne(i,t,n)),o=ar(ne(e,n,i)),a=ar(ne(e,n,t));return!!(r!==s&&o!==a||r===0&&sr(i,e,t)||s===0&&sr(i,n,t)||o===0&&sr(e,i,n)||a===0&&sr(e,t,n))}function sr(i,t,e){return t.x<=Math.max(i.x,e.x)&&t.x>=Math.min(i.x,e.x)&&t.y<=Math.max(i.y,e.y)&&t.y>=Math.min(i.y,e.y)}function ar(i){return i>0?1:i<0?-1:0}function Dm(i,t){let e=i;do{if(e.i!==i.i&&e.next.i!==i.i&&e.i!==t.i&&e.next.i!==t.i&&_l(e,e.next,i,t))return!0;e=e.next}while(e!==i);return!1}function Ri(i,t){return ne(i.prev,i,i.next)<0?ne(i,t,i.next)>=0&&ne(i,i.prev,t)>=0:ne(i,t,i.prev)<0||ne(i,i.next,t)<0}function Um(i,t){let e=i,n=!1;const r=(i.x+t.x)/2,s=(i.y+t.y)/2;do e.y>s!=e.next.y>s&&e.next.y!==e.y&&r<(e.next.x-e.x)*(s-e.y)/(e.next.y-e.y)+e.x&&(n=!n),e=e.next;while(e!==i);return n}function vl(i,t){const e=new Ss(i.i,i.x,i.y),n=new Ss(t.i,t.x,t.y),r=i.next,s=t.prev;return i.next=t,t.prev=i,e.next=r,r.prev=e,n.next=e,e.prev=n,s.next=n,n.prev=s,n}function Mo(i,t,e,n){const r=new Ss(i,t,e);return n?(r.next=n.next,r.prev=n,n.next.prev=r,n.next=r):(r.prev=r,r.next=r),r}function Ci(i){i.next.prev=i.prev,i.prev.next=i.next,i.prevZ&&(i.prevZ.nextZ=i.nextZ),i.nextZ&&(i.nextZ.prevZ=i.prevZ)}function Ss(i,t,e){this.i=i,this.x=t,this.y=e,this.prev=null,this.next=null,this.z=0,this.prevZ=null,this.nextZ=null,this.steiner=!1}function Im(i,t,e,n){let r=0;for(let s=t,o=e-n;s<e;s+=n)r+=(i[o]-i[s])*(i[s+1]+i[o+1]),o=s;return r}class dn{static area(t){const e=t.length;let n=0;for(let r=e-1,s=0;s<e;r=s++)n+=t[r].x*t[s].y-t[s].x*t[r].y;return n*.5}static isClockWise(t){return dn.area(t)<0}static triangulateShape(t,e){const n=[],r=[],s=[];So(t),yo(n,t);let o=t.length;e.forEach(So);for(let l=0;l<e.length;l++)r.push(o),o+=e[l].length,yo(n,e[l]);const a=vm.triangulate(n,r);for(let l=0;l<a.length;l+=3)s.push(a.slice(l,l+3));return s}}function So(i){const t=i.length;t>2&&i[t-1].equals(i[0])&&i.pop()}function yo(i,t){for(let e=0;e<t.length;e++)i.push(t[e].x),i.push(t[e].y)}class xl extends pe{constructor(t=new ml([new it(.5,.5),new it(-.5,.5),new it(-.5,-.5),new it(.5,-.5)]),e={}){super(),this.type="ExtrudeGeometry",this.parameters={shapes:t,options:e},t=Array.isArray(t)?t:[t];const n=this,r=[],s=[];for(let a=0,l=t.length;a<l;a++){const c=t[a];o(c)}this.setAttribute("position",new qt(r,3)),this.setAttribute("uv",new qt(s,2)),this.computeVertexNormals();function o(a){const l=[],c=e.curveSegments!==void 0?e.curveSegments:12,h=e.steps!==void 0?e.steps:1,u=e.depth!==void 0?e.depth:1;let d=e.bevelEnabled!==void 0?e.bevelEnabled:!0,m=e.bevelThickness!==void 0?e.bevelThickness:.2,_=e.bevelSize!==void 0?e.bevelSize:m-.1,M=e.bevelOffset!==void 0?e.bevelOffset:0,p=e.bevelSegments!==void 0?e.bevelSegments:3;const f=e.extrudePath,y=e.UVGenerator!==void 0?e.UVGenerator:Nm;let g,E=!1,P,w,b,U;f&&(g=f.getSpacedPoints(h),E=!0,d=!1,P=f.computeFrenetFrames(h,!1),w=new C,b=new C,U=new C),d||(p=0,m=0,_=0,M=0);const V=a.extractPoints(c);let v=V.shape;const A=V.holes;if(!dn.isClockWise(v)){v=v.reverse();for(let R=0,at=A.length;R<at;R++){const Y=A[R];dn.isClockWise(Y)&&(A[R]=Y.reverse())}}const K=dn.triangulateShape(v,A),L=v;for(let R=0,at=A.length;R<at;R++){const Y=A[R];v=v.concat(Y)}function k(R,at,Y){return at||console.error("THREE.ExtrudeGeometry: vec does not exist"),R.clone().addScaledVector(at,Y)}const z=v.length,J=K.length;function X(R,at,Y){let rt,$,_t;const dt=R.x-at.x,xt=R.y-at.y,Vt=Y.x-R.x,T=Y.y-R.y,x=dt*dt+xt*xt,H=dt*T-xt*Vt;if(Math.abs(H)>Number.EPSILON){const W=Math.sqrt(x),tt=Math.sqrt(Vt*Vt+T*T),j=at.x-xt/W,Lt=at.y+dt/W,wt=Y.x-T/tt,lt=Y.y+Vt/tt,ht=((wt-j)*T-(lt-Lt)*Vt)/(dt*T-xt*Vt);rt=j+dt*ht-R.x,$=Lt+xt*ht-R.y;const Dt=rt*rt+$*$;if(Dt<=2)return new it(rt,$);_t=Math.sqrt(Dt/2)}else{let W=!1;dt>Number.EPSILON?Vt>Number.EPSILON&&(W=!0):dt<-Number.EPSILON?Vt<-Number.EPSILON&&(W=!0):Math.sign(xt)===Math.sign(T)&&(W=!0),W?(rt=-xt,$=dt,_t=Math.sqrt(x)):(rt=dt,$=xt,_t=Math.sqrt(x/2))}return new it(rt/_t,$/_t)}const q=[];for(let R=0,at=L.length,Y=at-1,rt=R+1;R<at;R++,Y++,rt++)Y===at&&(Y=0),rt===at&&(rt=0),q[R]=X(L[R],L[Y],L[rt]);const nt=[];let et,gt=q.concat();for(let R=0,at=A.length;R<at;R++){const Y=A[R];et=[];for(let rt=0,$=Y.length,_t=$-1,dt=rt+1;rt<$;rt++,_t++,dt++)_t===$&&(_t=0),dt===$&&(dt=0),et[rt]=X(Y[rt],Y[_t],Y[dt]);nt.push(et),gt=gt.concat(et)}for(let R=0;R<p;R++){const at=R/p,Y=m*Math.cos(at*Math.PI/2),rt=_*Math.sin(at*Math.PI/2)+M;for(let $=0,_t=L.length;$<_t;$++){const dt=k(L[$],q[$],rt);Tt(dt.x,dt.y,-Y)}for(let $=0,_t=A.length;$<_t;$++){const dt=A[$];et=nt[$];for(let xt=0,Vt=dt.length;xt<Vt;xt++){const T=k(dt[xt],et[xt],rt);Tt(T.x,T.y,-Y)}}}const Pt=_+M;for(let R=0;R<z;R++){const at=d?k(v[R],gt[R],Pt):v[R];E?(b.copy(P.normals[0]).multiplyScalar(at.x),w.copy(P.binormals[0]).multiplyScalar(at.y),U.copy(g[0]).add(b).add(w),Tt(U.x,U.y,U.z)):Tt(at.x,at.y,0)}for(let R=1;R<=h;R++)for(let at=0;at<z;at++){const Y=d?k(v[at],gt[at],Pt):v[at];E?(b.copy(P.normals[R]).multiplyScalar(Y.x),w.copy(P.binormals[R]).multiplyScalar(Y.y),U.copy(g[R]).add(b).add(w),Tt(U.x,U.y,U.z)):Tt(Y.x,Y.y,u/h*R)}for(let R=p-1;R>=0;R--){const at=R/p,Y=m*Math.cos(at*Math.PI/2),rt=_*Math.sin(at*Math.PI/2)+M;for(let $=0,_t=L.length;$<_t;$++){const dt=k(L[$],q[$],rt);Tt(dt.x,dt.y,u+Y)}for(let $=0,_t=A.length;$<_t;$++){const dt=A[$];et=nt[$];for(let xt=0,Vt=dt.length;xt<Vt;xt++){const T=k(dt[xt],et[xt],rt);E?Tt(T.x,T.y+g[h-1].y,g[h-1].x+Y):Tt(T.x,T.y,u+Y)}}}G(),Q();function G(){const R=r.length/3;if(d){let at=0,Y=z*at;for(let rt=0;rt<J;rt++){const $=K[rt];Mt($[2]+Y,$[1]+Y,$[0]+Y)}at=h+p*2,Y=z*at;for(let rt=0;rt<J;rt++){const $=K[rt];Mt($[0]+Y,$[1]+Y,$[2]+Y)}}else{for(let at=0;at<J;at++){const Y=K[at];Mt(Y[2],Y[1],Y[0])}for(let at=0;at<J;at++){const Y=K[at];Mt(Y[0]+z*h,Y[1]+z*h,Y[2]+z*h)}}n.addGroup(R,r.length/3-R,0)}function Q(){const R=r.length/3;let at=0;pt(L,at),at+=L.length;for(let Y=0,rt=A.length;Y<rt;Y++){const $=A[Y];pt($,at),at+=$.length}n.addGroup(R,r.length/3-R,1)}function pt(R,at){let Y=R.length;for(;--Y>=0;){const rt=Y;let $=Y-1;$<0&&($=R.length-1);for(let _t=0,dt=h+p*2;_t<dt;_t++){const xt=z*_t,Vt=z*(_t+1),T=at+rt+xt,x=at+$+xt,H=at+$+Vt,W=at+rt+Vt;vt(T,x,H,W)}}}function Tt(R,at,Y){l.push(R),l.push(at),l.push(Y)}function Mt(R,at,Y){Gt(R),Gt(at),Gt(Y);const rt=r.length/3,$=y.generateTopUV(n,r,rt-3,rt-2,rt-1);At($[0]),At($[1]),At($[2])}function vt(R,at,Y,rt){Gt(R),Gt(at),Gt(rt),Gt(at),Gt(Y),Gt(rt);const $=r.length/3,_t=y.generateSideWallUV(n,r,$-6,$-3,$-2,$-1);At(_t[0]),At(_t[1]),At(_t[3]),At(_t[1]),At(_t[2]),At(_t[3])}function Gt(R){r.push(l[R*3+0]),r.push(l[R*3+1]),r.push(l[R*3+2])}function At(R){s.push(R.x),s.push(R.y)}}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}toJSON(){const t=super.toJSON(),e=this.parameters.shapes,n=this.parameters.options;return Fm(e,n,t)}static fromJSON(t,e){const n=[];for(let s=0,o=t.shapes.length;s<o;s++){const a=e[t.shapes[s]];n.push(a)}const r=t.options.extrudePath;return r!==void 0&&(t.options.extrudePath=new xs[r.type]().fromJSON(r)),new xl(n,t.options)}}const Nm={generateTopUV:function(i,t,e,n,r){const s=t[e*3],o=t[e*3+1],a=t[n*3],l=t[n*3+1],c=t[r*3],h=t[r*3+1];return[new it(s,o),new it(a,l),new it(c,h)]},generateSideWallUV:function(i,t,e,n,r,s){const o=t[e*3],a=t[e*3+1],l=t[e*3+2],c=t[n*3],h=t[n*3+1],u=t[n*3+2],d=t[r*3],m=t[r*3+1],_=t[r*3+2],M=t[s*3],p=t[s*3+1],f=t[s*3+2];return Math.abs(a-h)<Math.abs(o-c)?[new it(o,1-l),new it(c,1-u),new it(d,1-_),new it(M,1-f)]:[new it(a,1-l),new it(h,1-u),new it(m,1-_),new it(p,1-f)]}};function Fm(i,t,e){if(e.shapes=[],Array.isArray(i))for(let n=0,r=i.length;n<r;n++){const s=i[n];e.shapes.push(s.uuid)}else e.shapes.push(i.uuid);return e.options=Object.assign({},t),t.extrudePath!==void 0&&(e.options.extrudePath=t.extrudePath.toJSON()),e}class Ml extends Mr{constructor(t=1,e=0){const n=(1+Math.sqrt(5))/2,r=[-1,n,0,1,n,0,-1,-n,0,1,-n,0,0,-1,n,0,1,n,0,-1,-n,0,1,-n,n,0,-1,n,0,1,-n,0,-1,-n,0,1],s=[0,11,5,0,5,1,0,1,7,0,7,10,0,10,11,1,5,9,5,11,4,11,10,2,10,7,6,7,1,8,3,9,4,3,4,2,3,2,6,3,6,8,3,8,9,4,9,5,2,4,11,6,2,10,8,6,7,9,8,1];super(r,s,t,e),this.type="IcosahedronGeometry",this.parameters={radius:t,detail:e}}static fromJSON(t){return new Ml(t.radius,t.detail)}}class Sl extends pe{constructor(t=new ml([new it(0,.5),new it(-.5,-.5),new it(.5,-.5)]),e=12){super(),this.type="ShapeGeometry",this.parameters={shapes:t,curveSegments:e};const n=[],r=[],s=[],o=[];let a=0,l=0;if(Array.isArray(t)===!1)c(t);else for(let h=0;h<t.length;h++)c(t[h]),this.addGroup(a,l,h),a+=l,l=0;this.setIndex(n),this.setAttribute("position",new qt(r,3)),this.setAttribute("normal",new qt(s,3)),this.setAttribute("uv",new qt(o,2));function c(h){const u=r.length/3,d=h.extractPoints(e);let m=d.shape;const _=d.holes;dn.isClockWise(m)===!1&&(m=m.reverse());for(let p=0,f=_.length;p<f;p++){const y=_[p];dn.isClockWise(y)===!0&&(_[p]=y.reverse())}const M=dn.triangulateShape(m,_);for(let p=0,f=_.length;p<f;p++){const y=_[p];m=m.concat(y)}for(let p=0,f=m.length;p<f;p++){const y=m[p];r.push(y.x,y.y,0),s.push(0,0,1),o.push(y.x,y.y)}for(let p=0,f=M.length;p<f;p++){const y=M[p],g=y[0]+u,E=y[1]+u,P=y[2]+u;n.push(g,E,P),l+=3}}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}toJSON(){const t=super.toJSON(),e=this.parameters.shapes;return Om(e,t)}static fromJSON(t,e){const n=[];for(let r=0,s=t.shapes.length;r<s;r++){const o=e[t.shapes[r]];n.push(o)}return new Sl(n,t.curveSegments)}}function Om(i,t){if(t.shapes=[],Array.isArray(i))for(let e=0,n=i.length;e<n;e++){const r=i[e];t.shapes.push(r.uuid)}else t.shapes.push(i.uuid);return t}class yl extends pe{constructor(t=1,e=32,n=16,r=0,s=Math.PI*2,o=0,a=Math.PI){super(),this.type="SphereGeometry",this.parameters={radius:t,widthSegments:e,heightSegments:n,phiStart:r,phiLength:s,thetaStart:o,thetaLength:a},e=Math.max(3,Math.floor(e)),n=Math.max(2,Math.floor(n));const l=Math.min(o+a,Math.PI);let c=0;const h=[],u=new C,d=new C,m=[],_=[],M=[],p=[];for(let f=0;f<=n;f++){const y=[],g=f/n;let E=0;f===0&&o===0?E=.5/e:f===n&&l===Math.PI&&(E=-.5/e);for(let P=0;P<=e;P++){const w=P/e;u.x=-t*Math.cos(r+w*s)*Math.sin(o+g*a),u.y=t*Math.cos(o+g*a),u.z=t*Math.sin(r+w*s)*Math.sin(o+g*a),_.push(u.x,u.y,u.z),d.copy(u).normalize(),M.push(d.x,d.y,d.z),p.push(w+E,1-g),y.push(c++)}h.push(y)}for(let f=0;f<n;f++)for(let y=0;y<e;y++){const g=h[f][y+1],E=h[f][y],P=h[f+1][y],w=h[f+1][y+1];(f!==0||o>0)&&m.push(g,E,w),(f!==n-1||l<Math.PI)&&m.push(E,P,w)}this.setIndex(m),this.setAttribute("position",new qt(_,3)),this.setAttribute("normal",new qt(M,3)),this.setAttribute("uv",new qt(p,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new yl(t.radius,t.widthSegments,t.heightSegments,t.phiStart,t.phiLength,t.thetaStart,t.thetaLength)}}class Ym extends tn{constructor(t){super(t),this.isRawShaderMaterial=!0,this.type="RawShaderMaterial"}}class Bm extends hi{constructor(t){super(),this.isMeshStandardMaterial=!0,this.defines={STANDARD:""},this.type="MeshStandardMaterial",this.color=new zt(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new zt(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=Go,this.normalScale=new it(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new ke,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.defines={STANDARD:""},this.color.copy(t.color),this.roughness=t.roughness,this.metalness=t.metalness,this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.emissive.copy(t.emissive),this.emissiveMap=t.emissiveMap,this.emissiveIntensity=t.emissiveIntensity,this.bumpMap=t.bumpMap,this.bumpScale=t.bumpScale,this.normalMap=t.normalMap,this.normalMapType=t.normalMapType,this.normalScale.copy(t.normalScale),this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.roughnessMap=t.roughnessMap,this.metalnessMap=t.metalnessMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.envMapIntensity=t.envMapIntensity,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.flatShading=t.flatShading,this.fog=t.fog,this}}class Jm extends Bm{constructor(t){super(),this.isMeshPhysicalMaterial=!0,this.defines={STANDARD:"",PHYSICAL:""},this.type="MeshPhysicalMaterial",this.anisotropyRotation=0,this.anisotropyMap=null,this.clearcoatMap=null,this.clearcoatRoughness=0,this.clearcoatRoughnessMap=null,this.clearcoatNormalScale=new it(1,1),this.clearcoatNormalMap=null,this.ior=1.5,Object.defineProperty(this,"reflectivity",{get:function(){return ae(2.5*(this.ior-1)/(this.ior+1),0,1)},set:function(e){this.ior=(1+.4*e)/(1-.4*e)}}),this.iridescenceMap=null,this.iridescenceIOR=1.3,this.iridescenceThicknessRange=[100,400],this.iridescenceThicknessMap=null,this.sheenColor=new zt(0),this.sheenColorMap=null,this.sheenRoughness=1,this.sheenRoughnessMap=null,this.transmissionMap=null,this.thickness=0,this.thicknessMap=null,this.attenuationDistance=1/0,this.attenuationColor=new zt(1,1,1),this.specularIntensity=1,this.specularIntensityMap=null,this.specularColor=new zt(1,1,1),this.specularColorMap=null,this._anisotropy=0,this._clearcoat=0,this._iridescence=0,this._sheen=0,this._transmission=0,this.setValues(t)}get anisotropy(){return this._anisotropy}set anisotropy(t){this._anisotropy>0!=t>0&&this.version++,this._anisotropy=t}get clearcoat(){return this._clearcoat}set clearcoat(t){this._clearcoat>0!=t>0&&this.version++,this._clearcoat=t}get iridescence(){return this._iridescence}set iridescence(t){this._iridescence>0!=t>0&&this.version++,this._iridescence=t}get sheen(){return this._sheen}set sheen(t){this._sheen>0!=t>0&&this.version++,this._sheen=t}get transmission(){return this._transmission}set transmission(t){this._transmission>0!=t>0&&this.version++,this._transmission=t}copy(t){return super.copy(t),this.defines={STANDARD:"",PHYSICAL:""},this.anisotropy=t.anisotropy,this.anisotropyRotation=t.anisotropyRotation,this.anisotropyMap=t.anisotropyMap,this.clearcoat=t.clearcoat,this.clearcoatMap=t.clearcoatMap,this.clearcoatRoughness=t.clearcoatRoughness,this.clearcoatRoughnessMap=t.clearcoatRoughnessMap,this.clearcoatNormalMap=t.clearcoatNormalMap,this.clearcoatNormalScale.copy(t.clearcoatNormalScale),this.ior=t.ior,this.iridescence=t.iridescence,this.iridescenceMap=t.iridescenceMap,this.iridescenceIOR=t.iridescenceIOR,this.iridescenceThicknessRange=[...t.iridescenceThicknessRange],this.iridescenceThicknessMap=t.iridescenceThicknessMap,this.sheen=t.sheen,this.sheenColor.copy(t.sheenColor),this.sheenColorMap=t.sheenColorMap,this.sheenRoughness=t.sheenRoughness,this.sheenRoughnessMap=t.sheenRoughnessMap,this.transmission=t.transmission,this.transmissionMap=t.transmissionMap,this.thickness=t.thickness,this.thicknessMap=t.thicknessMap,this.attenuationDistance=t.attenuationDistance,this.attenuationColor.copy(t.attenuationColor),this.specularIntensity=t.specularIntensity,this.specularIntensityMap=t.specularIntensityMap,this.specularColor.copy(t.specularColor),this.specularColorMap=t.specularColorMap,this}}class yr extends ue{constructor(t,e=1){super(),this.isLight=!0,this.type="Light",this.color=new zt(t),this.intensity=e}dispose(){}copy(t,e){return super.copy(t,e),this.color.copy(t.color),this.intensity=t.intensity,this}toJSON(t){const e=super.toJSON(t);return e.object.color=this.color.getHex(),e.object.intensity=this.intensity,this.groundColor!==void 0&&(e.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(e.object.distance=this.distance),this.angle!==void 0&&(e.object.angle=this.angle),this.decay!==void 0&&(e.object.decay=this.decay),this.penumbra!==void 0&&(e.object.penumbra=this.penumbra),this.shadow!==void 0&&(e.object.shadow=this.shadow.toJSON()),e}}class Zm extends yr{constructor(t,e,n){super(t,n),this.isHemisphereLight=!0,this.type="HemisphereLight",this.position.copy(ue.DEFAULT_UP),this.updateMatrix(),this.groundColor=new zt(e)}copy(t,e){return super.copy(t,e),this.groundColor.copy(t.groundColor),this}}const ls=new Jt,Eo=new C,To=new C;class El{constructor(t){this.camera=t,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new it(512,512),this.map=null,this.mapPass=null,this.matrix=new Jt,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new Cs,this._frameExtents=new it(1,1),this._viewportCount=1,this._viewports=[new te(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(t){const e=this.camera,n=this.matrix;Eo.setFromMatrixPosition(t.matrixWorld),e.position.copy(Eo),To.setFromMatrixPosition(t.target.matrixWorld),e.lookAt(To),e.updateMatrixWorld(),ls.multiplyMatrices(e.projectionMatrix,e.matrixWorldInverse),this._frustum.setFromProjectionMatrix(ls),n.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),n.multiply(ls)}getViewport(t){return this._viewports[t]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(t){return this.camera=t.camera.clone(),this.bias=t.bias,this.radius=t.radius,this.mapSize.copy(t.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){const t={};return this.bias!==0&&(t.bias=this.bias),this.normalBias!==0&&(t.normalBias=this.normalBias),this.radius!==1&&(t.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(t.mapSize=this.mapSize.toArray()),t.camera=this.camera.toJSON(!1).object,delete t.camera.matrix,t}}const Ao=new Jt,Mi=new C,cs=new C;class zm extends El{constructor(){super(new Pe(90,1,.5,500)),this.isPointLightShadow=!0,this._frameExtents=new it(4,2),this._viewportCount=6,this._viewports=[new te(2,1,1,1),new te(0,1,1,1),new te(3,1,1,1),new te(1,1,1,1),new te(3,0,1,1),new te(1,0,1,1)],this._cubeDirections=[new C(1,0,0),new C(-1,0,0),new C(0,0,1),new C(0,0,-1),new C(0,1,0),new C(0,-1,0)],this._cubeUps=[new C(0,1,0),new C(0,1,0),new C(0,1,0),new C(0,1,0),new C(0,0,1),new C(0,0,-1)]}updateMatrices(t,e=0){const n=this.camera,r=this.matrix,s=t.distance||n.far;s!==n.far&&(n.far=s,n.updateProjectionMatrix()),Mi.setFromMatrixPosition(t.matrixWorld),n.position.copy(Mi),cs.copy(n.position),cs.add(this._cubeDirections[e]),n.up.copy(this._cubeUps[e]),n.lookAt(cs),n.updateMatrixWorld(),r.makeTranslation(-Mi.x,-Mi.y,-Mi.z),Ao.multiplyMatrices(n.projectionMatrix,n.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Ao)}}class Km extends yr{constructor(t,e,n=0,r=2){super(t,e),this.isPointLight=!0,this.type="PointLight",this.distance=n,this.decay=r,this.shadow=new zm}get power(){return this.intensity*4*Math.PI}set power(t){this.intensity=t/(4*Math.PI)}dispose(){this.shadow.dispose()}copy(t,e){return super.copy(t,e),this.distance=t.distance,this.decay=t.decay,this.shadow=t.shadow.clone(),this}}class Gm extends El{constructor(){super(new tl(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}}class $m extends yr{constructor(t,e){super(t,e),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(ue.DEFAULT_UP),this.updateMatrix(),this.target=new ue,this.shadow=new Gm}dispose(){this.shadow.dispose()}copy(t){return super.copy(t),this.target=t.target.clone(),this.shadow=t.shadow.clone(),this}}class jm extends yr{constructor(t,e){super(t,e),this.isAmbientLight=!0,this.type="AmbientLight"}}class Qm{constructor(t=!0){this.autoStart=t,this.startTime=0,this.oldTime=0,this.elapsedTime=0,this.running=!1}start(){this.startTime=bo(),this.oldTime=this.startTime,this.elapsedTime=0,this.running=!0}stop(){this.getElapsedTime(),this.running=!1,this.autoStart=!1}getElapsedTime(){return this.getDelta(),this.elapsedTime}getDelta(){let t=0;if(this.autoStart&&!this.running)return this.start(),0;if(this.running){const e=bo();t=(e-this.oldTime)/1e3,this.oldTime=e,this.elapsedTime+=t}return t}}function bo(){return(typeof performance>"u"?Date:performance).now()}const wo=new Jt;class tg{constructor(t,e,n=0,r=1/0){this.ray=new ws(t,e),this.near=n,this.far=r,this.camera=null,this.layers=new Rs,this.params={Mesh:{},Line:{threshold:1},LOD:{},Points:{threshold:1},Sprite:{}}}set(t,e){this.ray.set(t,e)}setFromCamera(t,e){e.isPerspectiveCamera?(this.ray.origin.setFromMatrixPosition(e.matrixWorld),this.ray.direction.set(t.x,t.y,.5).unproject(e).sub(this.ray.origin).normalize(),this.camera=e):e.isOrthographicCamera?(this.ray.origin.set(t.x,t.y,(e.near+e.far)/(e.near-e.far)).unproject(e),this.ray.direction.set(0,0,-1).transformDirection(e.matrixWorld),this.camera=e):console.error("THREE.Raycaster: Unsupported camera type: "+e.type)}setFromXRController(t){return wo.identity().extractRotation(t.matrixWorld),this.ray.origin.setFromMatrixPosition(t.matrixWorld),this.ray.direction.set(0,0,-1).applyMatrix4(wo),this}intersectObject(t,e=!0,n=[]){return ys(t,this,n,e),n.sort(Ro),n}intersectObjects(t,e=!0,n=[]){for(let r=0,s=t.length;r<s;r++)ys(t[r],this,n,e);return n.sort(Ro),n}}function Ro(i,t){return i.distance-t.distance}function ys(i,t,e,n){if(i.layers.test(t.layers)&&i.raycast(t,e),n===!0){const r=i.children;for(let s=0,o=r.length;s<o;s++)ys(r[s],t,e,!0)}}class eg{constructor(t=1,e=0,n=0){return this.radius=t,this.phi=e,this.theta=n,this}set(t,e,n){return this.radius=t,this.phi=e,this.theta=n,this}copy(t){return this.radius=t.radius,this.phi=t.phi,this.theta=t.theta,this}makeSafe(){return this.phi=Math.max(1e-6,Math.min(Math.PI-1e-6,this.phi)),this}setFromVector3(t){return this.setFromCartesianCoords(t.x,t.y,t.z)}setFromCartesianCoords(t,e,n){return this.radius=Math.sqrt(t*t+e*e+n*n),this.radius===0?(this.theta=0,this.phi=0):(this.theta=Math.atan2(t,n),this.phi=Math.acos(ae(e/this.radius,-1,1))),this}clone(){return new this.constructor().copy(this)}}class ng extends Ls{constructor(t=10,e=10,n=4473924,r=8947848){n=new zt(n),r=new zt(r);const s=e/2,o=t/e,a=t/2,l=[],c=[];for(let d=0,m=0,_=-a;d<=e;d++,_+=o){l.push(-a,0,_,a,0,_),l.push(_,0,-a,_,0,a);const M=d===s?n:r;M.toArray(c,m),m+=3,M.toArray(c,m),m+=3,M.toArray(c,m),m+=3,M.toArray(c,m),m+=3}const h=new pe;h.setAttribute("position",new qt(l,3)),h.setAttribute("color",new qt(c,3));const u=new xr({vertexColors:!0,toneMapped:!1});super(h,u),this.type="GridHelper"}dispose(){this.geometry.dispose(),this.material.dispose()}}class ig extends Ls{constructor(t,e=16776960){const n=new Uint16Array([0,1,1,2,2,3,3,0,4,5,5,6,6,7,7,4,0,4,1,5,2,6,3,7]),r=[1,1,1,-1,1,1,-1,-1,1,1,-1,1,1,1,-1,-1,1,-1,-1,-1,-1,1,-1,-1],s=new pe;s.setIndex(new Le(n,1)),s.setAttribute("position",new qt(r,3)),super(s,new xr({color:e,toneMapped:!1})),this.box=t,this.type="Box3Helper",this.geometry.computeBoundingSphere()}updateMatrixWorld(t){const e=this.box;e.isEmpty()||(e.getCenter(this.position),e.getSize(this.scale),this.scale.multiplyScalar(.5),super.updateMatrixWorld(t))}dispose(){this.geometry.dispose(),this.material.dispose()}}class rg extends Ls{constructor(t=1){const e=[0,0,0,t,0,0,0,0,0,0,t,0,0,0,0,0,0,t],n=[1,0,0,1,.6,0,0,1,0,.6,1,0,0,0,1,0,.6,1],r=new pe;r.setAttribute("position",new qt(e,3)),r.setAttribute("color",new qt(n,3));const s=new xr({vertexColors:!0,toneMapped:!1});super(r,s),this.type="AxesHelper"}setColors(t,e,n){const r=new zt,s=this.geometry.attributes.color.array;return r.set(t),r.toArray(s,0),r.toArray(s,3),r.set(e),r.toArray(s,6),r.toArray(s,9),r.set(n),r.toArray(s,12),r.toArray(s,15),this.geometry.attributes.color.needsUpdate=!0,this}dispose(){this.geometry.dispose(),this.material.dispose()}}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:Es}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__=Es);export{sc as $,Ln as A,Li as B,Is as C,$m as D,li as E,qt as F,er as G,Zm as H,Xm as I,Ai as J,Qm as K,Ym as L,Bm as M,hn as N,ue as O,Pe as P,Pi as Q,ws as R,Wm as S,Vm as T,ah as U,C as V,tm as W,Yt as X,$t as Y,ic as Z,rc as _,yl as a,ac as a0,lc as a1,cc as a2,Vs as a3,Yo as a4,Ee as a5,Wa as a6,Ll as a7,ig as a8,In as a9,tg as aa,ol as ab,jm as ac,ng as ad,rg as ae,Oe as b,Hm as c,eg as d,it as e,Tn as f,km as g,qm as h,ps as i,zt as j,Jm as k,Ma as l,ml as m,xl as n,ze as o,fl as p,je as q,ke as r,pl as s,Sl as t,dl as u,Ml as v,Km as w,tl as x,pe as y,tn as z};
