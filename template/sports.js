(function () {
  var editionNode = document.getElementById('edition');
  if (!editionNode) return;

  var edition;
  try { edition = JSON.parse(editionNode.textContent); } catch (e) { return; }
  var sports = edition.sports;
  if (!sports) return;

  var TEAM_WORDMARK = {
    'leafs': 'LEAFS',
    'raptors': 'RAPTORS',
    'blue-jays': 'BLUE JAYS'
  };

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function safeUrl(value) {
    try {
      var url = new URL(String(value || ''), window.location.href);
      if (url.protocol === 'http:' || url.protocol === 'https:') return url.href;
    } catch (e) {}
    return '';
  }

  function words(value) {
    return String(value || '').replace(/[-_]+/g, ' ').replace(/\b\w/g, function (c) {
      return c.toUpperCase();
    });
  }

  function torontoWhen(iso) {
    if (!iso) return '';
    var value = new Date(iso);
    if (isNaN(value.getTime())) return '';
    var date = value.toLocaleDateString('en-CA', {
      timeZone: 'America/Toronto', weekday: 'short', month: 'short', day: 'numeric'
    });
    var time = value.toLocaleTimeString('en-CA', {
      timeZone: 'America/Toronto', hour: 'numeric', minute: '2-digit'
    });
    return date + ' · ' + time;
  }

  function gamePlace(game) {
    if (!game) return '';
    return game.home_away === 'home' ? 'vs' : '@';
  }

  function gameScore(game) {
    if (!game || game.team_score == null || game.opponent_score == null) return '';
    return esc(game.team_score) + '–' + esc(game.opponent_score);
  }

  function standingText(standing) {
    if (!standing) return '';
    if (standing.label) return standing.label;
    var bits = [];
    if (standing.rank != null) bits.push('#' + standing.rank);
    if (standing.scope) bits.push(standing.scope);
    if (standing.games_back) bits.push(standing.games_back + ' GB');
    return bits.join(' · ');
  }

  function factHtml(label, value, extraClass) {
    if (!value) return '';
    return '<div class="sports-fact"><span class="sports-fact-label">' + esc(label) + '</span>' +
      '<span class="sports-fact-value' + (extraClass ? ' ' + extraClass : '') + '">' +
      esc(value) + '</span></div>';
  }

  function teamHeadlineHtml(headline) {
    if (!headline || !headline.headline) return '';
    var href = safeUrl(headline.url);
    var meta = [headline.source, words(headline.significance)].filter(Boolean).join(' · ');
    var inner = '<span class="sports-story-label">Major update</span>' +
      '<span class="sports-story-title">' + esc(headline.headline) + '</span>' +
      (headline.description ? '<span class="sports-story-dek">' + esc(headline.description) + '</span>' : '') +
      (meta ? '<span class="sports-story-meta">' + esc(meta) + '</span>' : '');
    if (!href) return '<div class="sports-team-story">' + inner + '</div>';
    return '<a class="sports-team-story" href="' + esc(href) + '" target="_blank" rel="noopener">' +
      inner + '</a>';
  }

  function teamRowHtml(row) {
    var snapshot = (row || {}).snapshot || {};
    var team = snapshot.team || {};
    var phase = snapshot.phase || 'offseason';
    var key = team.key || '';
    var name = TEAM_WORDMARK[key] || team.name || key;
    var league = team.league || '';
    var phaseClass = phase === 'postseason' ? ' postseason' : '';
    var head = '<div class="sports-team-head"><div class="sports-team-name">' + esc(name) +
      (league ? '<span class="sports-team-league">' + esc(league) + '</span>' : '') +
      '</div><div class="sports-phase' + phaseClass + '">' + esc(words(phase)) + '</div></div>';

    var body = '';
    if (!snapshot.available) {
      body = '<div class="sports-status-line"><strong>Unavailable</strong> · Score data could not be verified this morning.</div>';
    } else if (phase === 'offseason') {
      var offNext = snapshot.next_game;
      body = '<div class="sports-status-line"><strong>Offseason</strong>' +
        (offNext ? ' · Next: ' + esc(gamePlace(offNext) + ' ' + offNext.opponent + ' · ' + torontoWhen(offNext.start_time_toronto || offNext.start_time_utc)) : '') +
        '</div>';
    } else {
      var last = snapshot.last_game;
      if (last) {
        var resultLabel = last.result || words(last.status || 'Final');
        var score = gameScore(last);
        var opponent = gamePlace(last) + ' ' + (last.opponent || 'Opponent');
        body += '<div class="sports-scoreline"><span class="sports-result">' + esc(resultLabel) + '</span>' +
          (score ? '<span class="sports-score">' + score + '</span>' : '') +
          '<span class="sports-opponent">' + esc(opponent) + '</span></div>';
      }

      var next = snapshot.next_game;
      var nextText = '';
      if (next) {
        var nextStatus = String(next.status || '').toLowerCase();
        if (nextStatus === 'postponed' || nextStatus === 'cancelled') {
          nextText = words(nextStatus) + ' · ' + gamePlace(next) + ' ' + next.opponent;
        } else {
          nextText = gamePlace(next) + ' ' + next.opponent + ' · ' + torontoWhen(next.start_time_toronto || next.start_time_utc);
        }
      }
      var facts = factHtml('Record', snapshot.record && snapshot.record.display) +
        factHtml('Standing', standingText(snapshot.standing)) +
        factHtml('Next', nextText, 'sports-next-time');
      if (facts) body += '<div class="sports-facts">' + facts + '</div>';
      if (!last && !facts) {
        body += '<div class="sports-status-line">No current game state is available.</div>';
      }
    }

    return '<article class="sports-team" data-sports-team="' + esc(key) + '">' + head + body +
      teamHeadlineHtml(row && row.headline) + '</article>';
  }

  function matchTeamsHtml(match) {
    function one(name) {
      var cls = String(name || '').toLowerCase() === 'canada' ? ' class="sports-canada"' : '';
      return '<span' + cls + '>' + esc(name) + '</span>';
    }
    return one(match.home_team) + ' <span aria-hidden="true">v</span> ' + one(match.away_team);
  }

  function eventMatchHtml(match) {
    var status = String(match.status || '').toLowerCase();
    var final = status === 'final';
    var score = final && match.home_score != null && match.away_score != null
      ? esc(match.home_score) + '–' + esc(match.away_score)
      : torontoWhen(match.start_time_toronto || match.start_time_utc);
    if (status === 'postponed' || status === 'cancelled') score = words(status);
    var meta = [match.stage ? words(match.stage) : '', match.detail || ''].filter(Boolean).join(' · ');
    return '<div class="sports-match"><div class="sports-match-teams">' + matchTeamsHtml(match) + '</div>' +
      '<div class="sports-match-score">' + esc(score) + '</div>' +
      (meta ? '<div class="sports-match-meta">' + esc(meta) + '</div>' : '') + '</div>';
  }

  function eventTableHtml(table) {
    if (!table || !(table.rows || []).length) return '';
    var rows = table.rows.map(function (row) {
      return '<tr' + (row.canada ? ' class="canada"' : '') + '><td>' + esc(row.position) + '</td>' +
        '<td>' + esc(row.team) + '</td><td>' + esc(row.played == null ? '–' : row.played) + '</td>' +
        '<td>' + esc(row.points == null ? '–' : row.points) + '</td>' +
        '<td class="sports-gd">' + esc(row.goal_difference == null ? '–' : row.goal_difference) + '</td></tr>';
    }).join('');
    return '<div class="sports-table-wrap"><div class="sports-table-label">' + esc(table.label || 'Table') + '</div>' +
      '<table class="sports-table"><thead><tr><th>#</th><th>Team</th><th>P</th><th>Pts</th><th class="sports-gd">GD</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>';
  }

  function highlightsHtml(items) {
    if (!(items || []).length) return '';
    return '<div class="sports-highlights">' + items.map(function (item) {
      var flags = [];
      if (item.canada) flags.push('Canada');
      if (item.world_record) flags.push('Record');
      if (item.final) flags.push('Final');
      return '<div class="sports-highlight"><div class="sports-highlight-title">' + esc(item.label) + '</div>' +
        '<div class="sports-highlight-detail">' + esc(item.detail) +
        (flags.length ? ' · ' + esc(flags.join(' · ')) : '') + '</div></div>';
    }).join('') + '</div>';
  }

  function eventHasContent(event) {
    if (!event) return false;
    if (!event.available) return !!event.event_mode;
    return (event.matches || []).length > 0 ||
      (event.highlights || []).length > 0 ||
      !!(event.standings && (event.standings.rows || []).length);
  }

  function eventHtml(event) {
    var head = '<div class="sports-event-head"><div class="sports-event-name">' + esc(event.label) + '</div>' +
      (event.event_mode ? '<div class="sports-event-mode">Event edition</div>' : '') + '</div>' +
      (event.source ? '<div class="sports-event-source">Source: ' + esc(event.source) + '</div>' : '');
    if (!event.available) {
      return '<article class="sports-event" data-sports-event="' + esc(event.key) + '">' + head +
        '<div class="sports-event-unavailable">Verified event data is unavailable this morning.</div></article>';
    }
    return '<article class="sports-event" data-sports-event="' + esc(event.key) + '">' + head +
      (event.matches || []).map(eventMatchHtml).join('') + eventTableHtml(event.standings) +
      highlightsHtml(event.highlights || []) + '</article>';
  }

  function majorEventsHtml(payload) {
    var events = (((payload || {}).major_events || {}).events || []).filter(eventHasContent);
    if (!events.length) return '';
    var eventMode = !!((payload || {}).major_events || {}).event_mode;
    return '<section class="sports-desk sports-events" aria-labelledby="sports-events-title">' +
      '<div class="desk-head"><h2 class="desk-title" id="sports-events-title">Major Events</h2>' +
      '<div class="desk-dek">' + (eventMode ? 'Tournament edition · the important state, still bounded' : 'Only competitions with something worth knowing this morning') + '</div></div>' +
      events.map(eventHtml).join('') + '</section>';
  }

  function majorHeadlineHtml(item) {
    var href = safeUrl(item.url);
    var eventLabel = item.event_key ? words(item.event_key.replace(/-20\d\d$/, '')) : 'Major sport';
    var inner = '<span class="sports-story-label">' + esc(eventLabel) + '</span>' +
      '<span class="sports-story-title">' + esc(item.headline) + '</span>' +
      (item.description ? '<span class="sports-story-dek">' + esc(item.description) + '</span>' : '') +
      (item.source ? '<span class="sports-story-meta">' + esc(item.source) + '</span>' : '');
    if (!href) return '<div class="sports-major-story">' + inner + '</div>';
    return '<a class="sports-major-story" href="' + esc(href) + '" target="_blank" rel="noopener">' + inner + '</a>';
  }

  function majorHeadlinesHtml(payload) {
    var items = (payload || {}).major_headlines || [];
    if (!items.length) return '';
    return '<section class="sports-desk sports-headlines" aria-labelledby="sports-headlines-title">' +
      '<div class="desk-head"><h2 class="desk-title" id="sports-headlines-title">Major Headlines</h2>' +
      '<div class="desk-dek">Exceptional developments only</div></div>' +
      items.map(majorHeadlineHtml).join('') + '</section>';
  }

  function sportsHtml(payload) {
    var toronto = (payload || {}).toronto || [];
    var torontoHtml = '<section class="sports-desk sports-toronto" aria-labelledby="sports-toronto-title">' +
      '<div class="desk-head"><h2 class="desk-title" id="sports-toronto-title">Toronto</h2>' +
      '<div class="desk-dek">Leafs · Raptors · Blue Jays</div></div>' +
      toronto.map(teamRowHtml).join('') + '</section>';
    return torontoHtml + majorEventsHtml(payload) + majorHeadlinesHtml(payload);
  }

  function renderIfActive() {
    var tab = document.querySelector('.tab.active[data-tab="sports"]');
    var stories = document.getElementById('stories');
    if (!tab || !stories) return;
    stories.innerHTML = sportsHtml(sports);
    stories.setAttribute('data-sports-rendered', 'true');
  }

  var sportsTab = document.querySelector('[data-tab="sports"]');
  if (!sportsTab) return;
  sportsTab.addEventListener('click', function () {
    window.setTimeout(renderIfActive, 0);
  });
  renderIfActive();
})();
