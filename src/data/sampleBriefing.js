export const SAMPLE_BRIEFING = {
  id: '2026-03-09',
  date: 'March 9, 2026',
  system_status: {
    condition: 'ELEVATED',
    indicator: 'VOLATILE'
  },
  today_in_60_seconds: [
    {
      id: 'story-energy-hormuz',
      icon: '🛢️',
      headline: 'Oil volatility spikes following unconfirmed drone activity',
      domain: 'ENERGY',
      summary:
        'Brent crude briefly crossed $100 before reversing. Options flows suggest traders are aggressively repricing tail-risk for maritime supply chain interruptions over the next 48 hours.',
      signal_type: 'SIGNAL_SHIFT',
      status: 'ESCALATING',
      target: 'Strait of Hormuz',
      metric: '+17.1% VOL'
    },
    {
      id: 'story-global-rates',
      icon: '📉',
      headline: 'Markets reprice inflation risk path',
      domain: 'MACRO',
      signal_type: 'CONTINUING_SIGNAL',
      status: 'VOLATILE',
      target: 'Front-End Yields',
      metric: 'REPRICING'
    },
    {
      id: 'story-sovereign-ai-compute',
      icon: '🤖',
      headline: 'China accelerates sovereign compute infrastructure',
      domain: 'TECH',
      signal_type: 'CONTINUING_SIGNAL',
      status: 'HIGH',
      target: 'Domestic Datacenters',
      metric: 'CAPEX SURGE'
    },
    {
      id: 'story-pentagon-ai-governance',
      icon: '⚖️',
      headline: 'Pentagon-AI governance friction delays deployments',
      domain: 'DEFENSE',
      signal_type: 'SIGNAL_SHIFT',
      status: 'MONITOR',
      target: 'Autonomous Systems',
      metric: 'DELAYED'
    },
    {
      id: 'story-ecb-rate-path',
      icon: '🌍',
      headline: 'ECB signals hawkish hold on rate cuts',
      domain: 'MACRO',
      signal_type: 'SIGNAL_SHIFT',
      status: 'STABILIZING',
      target: 'EUR/USD',
      metric: 'HAWKISH'
    }
  ],
  what_changed: {
    new: [
      'War-risk insurance costs jumped again for Gulf-linked commercial shipping routes.',
      'ECB messaging hardened around the risk of energy-led inflation persistence.'
    ],
    intensified: [
      'Oil volatility is now feeding directly into front-end rate pricing and cross-asset hedging.',
      'Competition for sovereign AI capacity is expanding from technology policy into energy and industrial planning.'
    ],
    eased: [
      'The most acute fear of a full maritime halt eased after some vessels resumed rerouted passage.'
    ],
    changed_meaning: [
      'The Hormuz story is no longer a regional disruption alone; it has become a macro transmission channel.',
      'AI infrastructure is no longer just a technology race; it is becoming a state-capacity and strategic autonomy issue.'
    ]
  },
  major_developments: [
    {
      id: 'dev-1',
      story_id: 'story-energy-hormuz',
      domain: 'ENERGY',
      region: 'MIDDLE EAST',
      impact: 'CRITICAL',
      icon: '🛢️',
      change_type: 'ESCALATION',
      story_stage: 'PEAKING',
      headline: 'Oil Shock and War Risk',
      why_it_matters_now:
        'The disruption is now materially altering inflation expectations, shipping costs, and central-bank path assumptions.',
      executive_summary:
        'Oil surged nearly 30% before reversing as geopolitical tensions escalated and maritime risk began transmitting into macro pricing.',
      key_facts: [
        'Brent briefly crossed $100 before retracing as traders digested mixed security signals.',
        'Insurers widened Gulf transit premiums, lifting shipping costs within hours.',
        'Volatility spread from energy into rates, equities, and FX positioning.'
      ],
      next_watchpoints: [
        'Commercial vessel transit volumes through the Strait of Hormuz over the next 24 hours.',
        'Whether regional actors issue credible de-escalation signals or expand interdiction risk.'
      ],
      tags: ['energy', 'shipping', 'oil', 'inflation', 'middle-east'],
      sources: [
        { name: 'Reuters', url: 'https://www.reuters.com/world/middle-east/' },
        { name: 'Bloomberg', url: 'https://www.bloomberg.com/energy' },
        { name: 'Financial Times', url: 'https://www.ft.com/markets' }
      ]
    },
    {
      id: 'dev-2',
      story_id: 'story-sovereign-ai-compute',
      domain: 'TECH',
      region: 'GLOBAL',
      impact: 'HIGH',
      icon: '🤖',
      change_type: 'UPDATE',
      story_stage: 'ESCALATING',
      headline: 'Sovereign AI Compute Race',
      why_it_matters_now:
        'The story is widening from chip access into datacenter siting, energy allocation, and state-backed capital deployment.',
      executive_summary:
        'Nations are increasingly treating high-tier compute clusters as critical national infrastructure.',
      key_facts: [
        'New export control proposals are tightening access to advanced accelerator supply.',
        'Sovereign and state-linked capital is moving into domestic datacenter buildout.',
        'Talent recruitment and power availability are now strategic bottlenecks.'
      ],
      next_watchpoints: [
        'Additional export-control coordination between the US and allies.',
        'Announcements on power allocation, permits, or domestic compute subsidies.'
      ],
      tags: ['ai', 'compute', 'industrial-policy', 'chips', 'state-capacity'],
      sources: [
        { name: 'Wall Street Journal', url: 'https://www.wsj.com/tech' },
        { name: 'TechCrunch', url: 'https://techcrunch.com/tag/ai/' },
        { name: 'US State Department', url: 'https://www.state.gov/' }
      ]
    },
    {
      id: 'dev-3',
      story_id: 'story-global-rates',
      domain: 'MACRO',
      region: 'GLOBAL',
      impact: 'HIGH',
      icon: '📉',
      change_type: 'ESCALATION',
      story_stage: 'ESCALATING',
      headline: 'Inflation Path Repriced',
      why_it_matters_now:
        'This has shifted from a rates debate to a cross-asset repricing event driven by geopolitical inflation risk.',
      executive_summary:
        'Bond and equity desks are resetting expectations for the timing and depth of rate cuts.',
      key_facts: [
        'Front-end yields rose as inflation hedges widened after the energy shock.',
        'Cross-asset volatility expanded beyond energy-sensitive sectors into broader macro positioning.',
        'FX desks repositioned around renewed dollar strength and policy divergence risk.'
      ],
      next_watchpoints: [
        'Whether the next inflation prints confirm pass-through from energy into broader expectations.',
        'Any central-bank communication that reframes the likely path of cuts.'
      ],
      tags: ['macro', 'rates', 'inflation', 'fx', 'policy'],
      sources: [
        { name: 'Bloomberg', url: 'https://www.bloomberg.com/markets' },
        { name: 'Financial Times', url: 'https://www.ft.com/markets' },
        { name: 'Reuters', url: 'https://www.reuters.com/markets/' }
      ]
    },
    {
      id: 'dev-4',
      story_id: 'story-pentagon-ai-governance',
      domain: 'DEFENSE',
      region: 'UNITED STATES',
      impact: 'MEDIUM',
      icon: '⚖️',
      change_type: 'UPDATE',
      story_stage: 'EMERGING',
      headline: 'Pentagon-AI Governance Friction',
      why_it_matters_now:
        'Today clarified that the bottleneck is not demand for deployment but governance confidence around auditability and control.',
      executive_summary:
        'Procurement urgency is colliding with compliance, explainability, and operational control requirements.',
      key_facts: [
        'Program reviews slowed one autonomous systems deployment track.',
        'Vendors are being pushed to document model assurance and override logic more rigorously.',
        'Acquisition teams are splitting between speed and auditability priorities.'
      ],
      next_watchpoints: [
        'Whether new assurance frameworks shorten approval times for autonomous systems.',
        'Any procurement guidance that standardizes model evaluation and operator override requirements.'
      ],
      tags: ['defense', 'ai', 'procurement', 'governance', 'autonomy'],
      sources: [
        { name: 'Defense One', url: 'https://www.defenseone.com/' },
        { name: 'Wall Street Journal', url: 'https://www.wsj.com/news/technology' },
        { name: 'US Department of Defense', url: 'https://www.defense.gov/' }
      ]
    },
    {
      id: 'dev-5',
      story_id: 'story-ecb-rate-path',
      domain: 'MACRO',
      region: 'EUROPE',
      impact: 'MEDIUM',
      icon: '🌍',
      change_type: 'UPDATE',
      story_stage: 'STABILIZING',
      headline: 'ECB Holds Hawkish Bias',
      why_it_matters_now:
        'The ECB is signaling less urgency to ease if energy volatility threatens a renewed inflation impulse.',
      executive_summary:
        'European rate-cut expectations are softening as policymakers weigh imported energy pressure against slowing growth.',
      key_facts: [
        'ECB messaging emphasized vigilance around second-round inflation effects.',
        'Rate-cut timing expectations shifted as energy volatility re-entered the policy conversation.',
        'EUR positioning firmed on the view that easing may be slower than previously expected.'
      ],
      next_watchpoints: [
        'Any follow-up ECB commentary that clarifies the threshold for delaying cuts.',
        'Whether sustained energy strength begins to alter eurozone inflation expectations materially.'
      ],
      tags: ['ecb', 'europe', 'rates', 'inflation', 'energy'],
      sources: [
        { name: 'Financial Times', url: 'https://www.ft.com/europe' },
        { name: 'Reuters', url: 'https://www.reuters.com/markets/europe/' },
        { name: 'European Central Bank', url: 'https://www.ecb.europa.eu/' }
      ]
    }
  ],
  timeline_context: {
    title: 'Middle East Escalation Sequence',
    events: [
      {
        date: 'MARCH 12, 2026',
        headline: 'Shipping disruption reports intensify',
        details:
          'Commercial routing desks flagged new insurance premiums and rerouting pressure across Gulf-linked cargo flows.'
      },
      {
        date: 'MARCH 11, 2026',
        headline: 'Energy desks widen hedging activity',
        details:
          'Options flows accelerated as traders repriced tail-risk around supply interruption and retaliatory action.'
      },
      {
        date: 'MARCH 10, 2026',
        headline: 'Back-channel diplomacy stalls',
        details:
          'Regional intermediaries reported reduced confidence that maritime security talks would stabilize near-term flows.'
      }
    ]
  },
  risk_matrix: {
    title: '24-Hour Threat Map',
    risks: [
      {
        id: 'risk-1',
        label: 'Hormuz transit shock',
        probability: 0.78,
        impact: 0.95,
        details: 'Would reprice energy, inflation, and shipping risk simultaneously.'
      },
      {
        id: 'risk-2',
        label: 'Oil spike mean reversion',
        probability: 0.64,
        impact: 0.34,
        details: 'Fast diplomatic signaling could unwind the most extreme front-end pricing.'
      },
      {
        id: 'risk-3',
        label: 'ECB hawkish spillover',
        probability: 0.41,
        impact: 0.71,
        details: 'A sustained energy move could harden developed-market rate expectations.'
      }
    ]
  },
  macro_indicators: [
    {
      id: 'ind-01',
      title: 'Brent Crude',
      metric: '7-DAY VOLATILITY',
      currentValue: '$98.40',
      trendValue: '+17.1%',
      trendDirection: 'up',
      data: [84, 86, 87, 89, 93, 96, 98.4],
      details:
        'Risk premium remains embedded as energy desks model further shipping disruption and retaliatory risk.'
    },
    {
      id: 'ind-02',
      title: 'Gold',
      metric: 'SAFE-HAVEN FLOW',
      currentValue: '$2,214',
      trendValue: '+3.1%',
      trendDirection: 'up',
      data: [2148, 2151, 2160, 2178, 2190, 2205, 2214],
      details:
        'Capital rotated into defensive stores of value as geopolitical uncertainty bled into broader macro positioning.'
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
