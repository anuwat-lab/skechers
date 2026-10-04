(() => {
 const status=document.getElementById('status');
 const form=document.getElementById('registerForm');
 async function api(url,options={}){const r=await fetch(url,{cache:'no-store',...options});const data=await r.json();if(r.status===401 && !form){location.replace('login.html');throw Error('กรุณาเข้าสู่ระบบ');}if(!r.ok)throw Error(data.error||'เชื่อมต่อไม่สำเร็จ');return data;}
 if(form){
  let info;const button=document.getElementById('submitRegistration');
  let requestId=sessionStorage.getItem('stompRegistrationRequest');
  if(!requestId){requestId=crypto.randomUUID();sessionStorage.setItem('stompRegistrationRequest',requestId);}
  api('api/registration-info').then(data=>{info=data;document.getElementById('consentText').textContent=data.consentText;document.getElementById('privacyText').textContent='เราใช้ชื่อ นามสกุล และเบอร์โทรของคุณเพื่อจัดการลงทะเบียนและติดต่อเกี่ยวกับกิจกรรมนี้ ไม่ได้ใช้สำหรับการตลาด การลงทะเบียนนี้ยังไม่รวมการยินยอมเผยแพร่ภาพถ่าย';button.disabled=false;}).catch(e=>status.textContent=e.message);
  form.addEventListener('submit',async event=>{event.preventDefault();if(!form.reportValidity()||!info)return;button.disabled=true;status.textContent='กำลังบันทึก…';const fields=new FormData(form);try{const result=await api('api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({firstName:fields.get('firstName'),lastName:fields.get('lastName'),phone:fields.get('phone'),consent:fields.get('consent')==='on',consentVersion:info.consentVersion,requestId})});form.hidden=true;document.getElementById('success').hidden=false;document.getElementById('queueNumber').textContent='#'+String(result.queue).padStart(3,'0');status.textContent='รหัสยืนยันที่เครื่องเกม: '+result.code;}catch(e){status.textContent=e.message;button.disabled=false;}});
 } else {
  let page=1;
  async function load(){status.textContent='กำลังโหลด…';try{const data=await api('api/registrations?page='+page+'&q='+encodeURIComponent(document.getElementById('search').value));const rows=document.getElementById('rows');rows.replaceChildren();for(const row of data.rows){const tr=document.createElement('tr');for(const value of ['#'+row.queue,row.first_name+' '+row.last_name,row.phone,new Date(row.created_at).toLocaleString('th-TH'), 'ยินยอม · '+row.consent_version,row.status==='claimed'?'ยืนยันรอบแล้ว':'รอเรียก']){const td=document.createElement('td');td.textContent=value;tr.append(td);}rows.append(tr);}document.getElementById('total').textContent='พบ '+data.total+' คน';document.getElementById('page').textContent='หน้า '+page;document.getElementById('previous').disabled=page<=1;document.getElementById('next').disabled=page*50>=data.total;status.textContent=data.rows.length?'':'ยังไม่มีข้อมูล';}catch(e){document.getElementById('rows').replaceChildren();status.textContent=e.message;}}
  document.getElementById('logout').onclick=async()=>{try{await api('api/admin-logout',{method:'POST'});location.replace('login.html');}catch(e){status.textContent=e.message;}};
  window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
  document.getElementById('refresh').onclick=()=>{page=1;load();};document.getElementById('previous').onclick=()=>{page=Math.max(1,page-1);load();};document.getElementById('next').onclick=()=>{page++;load();};load();
 }
})();
