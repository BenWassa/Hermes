export const SAMPLE_BRIEFING = {
  id: '2026-03-09',
  date: 'March 9, 2026',
  today_in_60_seconds: [
    { icon: '🛢️', headline: 'Oil volatility spikes' },
    { icon: '📉', headline: 'Markets reprice inflation risk' },
    { icon: '🤖', headline: 'China accelerates AI push' },
    { icon: '⚖️', headline: 'Pentagon-AI tension emerges' }
  ],
  major_developments: [
    {
      id: 'dev-1',
      icon: '🛢️',
      headline: 'Oil Shock and War Risk',
      executive_summary:
        'Oil surged nearly 30% before reversing as geopolitical tensions escalated.',
      key_facts: [
        'Brent briefly crossed $100',
        'De-escalation signals caused reversal',
        'Market volatility spread to equities'
      ],
      sources: ['Reuters', 'Bloomberg', 'FT']
    },
    {
      id: 'dev-2',
      icon: '🤖',
      headline: 'Sovereign AI Compute Race',
      executive_summary:
        'Nations are increasingly treating high-tier compute clusters as critical national infrastructure.',
      key_facts: [
        'New export controls proposed on advanced chips',
        'Middle Eastern sovereign wealth funds redirecting capital to domestic datacenters',
        'Talent acquisition becomes state-level priority'
      ],
      sources: ['WSJ', 'TechCrunch', 'State Dept']
    }
  ],
  analyst_consensus: {
    consensus: [
      'Energy shock could delay rate cuts globally.',
      'Defense and compute spending will remain non-cyclical.'
    ],
    friction: [
      'Some analysts believe the oil spike will reverse rapidly if conflict cools.',
      "Disagreement on whether the ECB will follow the Fed's hawkish tilt."
    ]
  },
  strategic_context: [
    'Energy shocks are reintroducing geopolitics into macroeconomic expectations.',
    'Persistent oil elevation could force central banks to maintain tighter policy despite slowing growth.',
    'The intersection of AI infrastructure demands and energy scarcity is becoming the defining macroeconomic theme of the decade.'
  ],
  watchlist:
    'Strait of Hormuz shipping flows over the next 48 hours may determine whether energy volatility persists and bleeds into core inflation metrics.'
};
