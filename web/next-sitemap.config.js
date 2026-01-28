const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://projectcivitas.com/api/v1";

/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: process.env.SITE_URL || "https://projectcivitas.com",
  generateRobotsTxt: true,
  changefreq: "daily",
  priority: 0.7,
  sitemapSize: 5000,
  robotsTxtOptions: {
    policies: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/admin/"],
      },
    ],
  },
  additionalPaths: async (config) => {
    const paths = [];

    // Fetch all objective IDs for /tracker/[id]
    try {
      const res = await fetch(`${API_BASE}/objectives?per_page=1000`);
      if (res.ok) {
        const data = await res.json();
        for (const item of data.items || []) {
          paths.push({
            loc: `/tracker/${item.id}`,
            changefreq: "weekly",
            priority: 0.6,
            lastmod: new Date().toISOString(),
          });
        }
      }
    } catch {
      /* skip if API unavailable */
    }

    // Fetch all executive order IDs for /executive-orders/[id]
    try {
      const res = await fetch(`${API_BASE}/executive-orders?per_page=500`);
      if (res.ok) {
        const data = await res.json();
        for (const item of data.items || []) {
          paths.push({
            loc: `/executive-orders/${item.id}`,
            changefreq: "monthly",
            priority: 0.7,
            lastmod: new Date().toISOString(),
          });
        }
      }
    } catch {
      /* skip */
    }

    // Fetch all case IDs for /cases/[id]
    try {
      const res = await fetch(`${API_BASE}/cases?per_page=500`);
      if (res.ok) {
        const data = await res.json();
        for (const item of data.items || []) {
          paths.push({
            loc: `/cases/${item.id}`,
            changefreq: "weekly",
            priority: 0.7,
            lastmod: new Date().toISOString(),
          });
        }
      }
    } catch {
      /* skip */
    }

    // Fetch all legislation IDs for /legislation/[id]
    try {
      const res = await fetch(
        `${API_BASE}/legislation?since=2017-01-01&matched_only=true&per_page=500`
      );
      if (res.ok) {
        const data = await res.json();
        for (const item of data.items || []) {
          paths.push({
            loc: `/legislation/${item.id}`,
            changefreq: "weekly",
            priority: 0.6,
            lastmod: new Date().toISOString(),
          });
        }
      }
    } catch {
      /* skip */
    }

    // State pages
    const stateCodes = [
      "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
      "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
      "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
      "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
      "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
    ];
    for (const code of stateCodes) {
      paths.push({
        loc: `/states/${code}`,
        changefreq: "weekly",
        priority: 0.5,
        lastmod: new Date().toISOString(),
      });
    }

    return paths;
  },
};
