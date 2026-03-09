async function check() {
  const slug = 'de-sns';
  // I need the ID to test ID filtering. I'll fetch the org list again just to grab the ID of 'de-sns'
  const orgsRes = await fetch('https://dados.gov.pt/api/1/organizations/?page_size=20');
  const orgs = await orgsRes.json();
  const target = orgs.data.find(o => o.slug === slug);
  
  if (!target) { console.log('Target not found'); return; }
  
  console.log('Target:', target.slug, target.id);
  
  // Test ID
  const idRes = await fetch(`https://dados.gov.pt/api/1/datasets/?organization=${target.id}&page_size=1`);
  const idData = await idRes.json();
  console.log('Total by ID:', idData.total);
  
  // Test Slug
  const slugRes = await fetch(`https://dados.gov.pt/api/1/datasets/?organization=${target.slug}&page_size=1`);
  const slugData = await slugRes.json();
  console.log('Total by Slug:', slugData.total);
}
check();
