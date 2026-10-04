(() => {
 const hint=document.getElementById('registrationHint'),img=document.getElementById('registrationQR'),retry=document.getElementById('retryRegistrationQR');
 async function load(){
  retry.disabled=true;
  try{
   const response=await fetch('api/registration-info',{cache:'no-store',signal:AbortSignal.timeout(6000)});
   if(!response.ok)throw Error('server');
   const data=await response.json(),url=new URL(data.url);
   hint.textContent=['127.0.0.1','localhost'].includes(url.hostname)?'QR ทดสอบในเครื่อง — ต้องตั้ง URL ออนไลน์ก่อนให้มือถือสแกนใช้งาน':'QR ลงทะเบียน: '+url.href;
   const candidate=new Image();
   candidate.onload=()=>{img.src=candidate.src;};
   candidate.onerror=()=>{hint.textContent='โหลด QR จากเซิร์ฟเวอร์ไม่ได้ กำลังแสดง QR ทดสอบในเครื่อง';};
   candidate.src='api/registration-qr.svg?t='+Date.now();
  }catch{hint.textContent='เชื่อมระบบไม่ได้ กำลังแสดง QR ทดสอบในเครื่อง — เปิด Start Smooth Stomp.command แล้วลองใหม่';}
  finally{retry.disabled=false;}
 }
 retry.addEventListener('click',load);load();
})();
