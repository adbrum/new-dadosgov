async function check() {
  try {
    // 1. Fetch organizations to find DE-SNS
    console.log('Fetching organizations...');
    const orgsRes = await fetch('https://dados.gov.pt/api/1/organizations/?page_size=100');
    const orgs = await orgsRes.json();
    
    // Find DE-SNS loosely
    const target = orgs.data.find(o => o.name.includes('Direção Executiva') && o.slug.includes('sns'));
    
    if (target) {
      console.log('Found Organization:', target.name);
      console.log('ID:', target.id);
      console.log('Slug:', target.slug);
      
      // 2. Try fetching datasets with ID
      console.log('\nTesting filter by ID:', target.id);
      const idRes = await fetch(`https://dados.gov.pt/api/1/datasets/?organization=${target.id}&page_size=1`);
      const idData = await idRes.json();
      console.log('Results using ID:', idData.total);

      // 3. Try fetching datasets with Slug
      console.log('\nTesting filter by Slug:', target.slug);
      const slugRes = await fetch(`https://dados.gov.pt/api/1/datasets/?organization=${target.slug}&page_size=1`);
      const slugData = await slugRes.json();
      console.log('Results using Slug:', slugData.total);
    } else {
      console.log('Could not find DE-SNS organization in first 100.');
      // Print first 5 just to see
      console.log('Sample orgs:', orgs.data.slice(0, 3).map(o => o.slug));
    }
  } catch (e) {
    console.error(e);
  }
}

check();
