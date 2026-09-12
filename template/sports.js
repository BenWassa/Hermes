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
  var TRUSTED_ASSET_HOSTS = {
    'assets.nhle.com': true,
    'cdn.nba.com': true,
    'www.mlbstatic.com': true,
    'a.espncdn.com': true,
    'secure.espncdn.com': true
  };
  var MARK_TIMEOUT_MS = 3500;

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

  function safeAssetUrl(value) {
    try {
      var url = new URL(String(value || ''));
      if (url.protocol === 'https:' && TRUSTED_ASSET_HOSTS[url.hostname]) return url.href;
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

  function sectionHeadHtml(kicker, title, deck, id) {
    return '<div class="desk-head sports-desk-head">' +
      '<div class="sports-section-kicker">' + esc(kicker) + '</div>' +
      '<h2 class="desk-title" id="' + esc(id) + '">' + esc(title) + '</h2>' +
      '<div class="desk-dek">' + esc(deck) + '</div></div>';
  }

  function teamMarkHtml(mark) {
    if (!mark) return '';
    var light = safeAssetUrl(mark.light);
    var dark = safeAssetUrl(mark.dark);
    if (!light) return '';
    var image = '<img src="' + esc(light) + '" alt="" aria-hidden="true" width="48" height="48" decoding="async" referrerpolicy="no-referrer">';
    if (dark) {
      image = '<picture><source media="(prefers-color-scheme: dark)" srcset="' + esc(dark) + '">' + image + '</picture>';
    }
    return '<span class="sports-mark sports-mark-loading" data-sports-mark aria-hidden="true">' + image +
      '<span class="sports-mark-fallback">' + esc(mark.fallback || '') + '</span></span>';
  }

  function crestHtml(url, tableMode) {
    var href = safeAssetUrl(url);
    if (!href) return '';
    var size = tableMode ? 24 : 30;
    return '<span class="sports-club-crest sports-mark-loading" data-sports-mark aria-hidden="true">' +
      '<img src="' + esc(href) + '" alt="" width="' + size + '" height="' + size + '" loading="lazy" decoding="async" fetchpriority="low" referrerpolicy="no-referrer">' +
      '</span>';
  }

  function settleMarks(root) {
    Array.prototype.forEach.call(root.querySelectorAll('[data-sports-mark]'), function (mark) {
      if (mark.getAttribute('data-wired') === 'true') return;
      mark.setAttribute('data-wired', 'true');
      var img = mark.querySelector('img');
      if (!img) { mark.classList.add('sports-mark-failed'); return; }
      var timer;
      function loaded() {
        window.clearTimeout(timer);
        mark.classList.remove('sports-mark-loading', 'sports-mark-failed');
        mark.classList.add('sports-mark-loaded');
      }
      function failed() {
        window.clearTimeout(timer);
        mark.classList.remove('sports-mark-loading', 'sports-mark-loaded');
        mark.classList.add('sports-mark-failed');
      }
      img.addEventListener('load', loaded, { once: true });
      img.addEventListener('error', failed, { once: true });
      timer = window.setTimeout(failed, MARK_TIMEOUT_MS);
      if (img.complete) {
        if (img.naturalWidth > 0) loaded(); else failed();
      }
    });
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
    return '<a class="sports-team-story" href="' + esc(href) + '" target="_blank" rel="noopener">' + inner + '</a>';
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
      if (!last && !facts) body += '<div class="sports-status-line">No current game state is available.</div>';
    }

    return '<article class="sports-team" data-sports-team="' + esc(key) + '">' + teamMarkHtml(row && row.mark) +
      '<div class="sports-team-copy">' + head + body + teamHeadlineHtml(row && row.headline) + '</div></article>';
  }

  function clubHtml(name, logoUrl, tableMode) {
    var cls = String(name || '').toLowerCase() === 'canada' ? ' sports-canada' : '';
    return '<span class="sports-club' + cls + '">' + crestHtml(logoUrl, tableMode) + '<span>' + esc(name) + '</span></span>';
  }

  function matchTeamsHtml(match) {
    return clubHtml(match.home_team, match.home_logo_url, false) +
      ' <span class="sports-versus" aria-hidden="true">v</span> ' +
      clubHtml(match.away_team, match.away_logo_url, false);
  }

  function eventMatchHtml(match, commonStage) {
    var status = String(match.status || '').toLowerCase();
    var final = status === 'final';
    var score = final && match.home_score != null && match.away_score != null
      ? esc(match.home_score) + '–' + esc(match.away_score)
      : torontoWhen(match.start_time_toronto || match.start_time_utc);
    if (status === 'postponed' || status === 'cancelled') score = words(status);
    var stage = match.stage && match.stage !== commonStage ? words(match.stage) : '';
    var meta = [stage, match.detail || ''].filter(Boolean).join(' · ');
    return '<div class="sports-match"><div class="sports-match-teams">' + matchTeamsHtml(match) + '</div>' +
      '<div class="sports-match-score">' + esc(score) + '</div>' +
      (meta ? '<div class="sports-match-meta">' + esc(meta) + '</div>' : '') + '</div>';
  }

  function commonEventStage(event) {
    var stages = (event.matches || []).map(function (match) { return match.stage || ''; }).filter(Boolean);
    if (!stages.length) return '';
    return stages.every(function (stage) { return stage === stages[0]; }) ? stages[0] : '';
  }

  function tableHasPositionGap(rows) {
    for (var i = 1; i < rows.length; i += 1) {
      if (Number(rows[i].position) > Number(rows[i - 1].position) + 1) return true;
    }
    return false;
  }

  function eventTableHtml(table, eventKey) {
    if (!table || !(table.rows || []).length) return '';
    var rowsData = table.rows || [];
    var isChampionsLeague = eventKey === 'champions-league';
    var hasGap = tableHasPositionGap(rowsData);
    var previousPosition = null;
    var rows = rowsData.map(function (row) {
      var prefix = '';
      if (previousPosition != null && Number(row.position) > Number(previousPosition) + 1) {
        prefix = '<tr class="sports-table-gap" aria-hidden="true"><td colspan="5"><span>Positions ' +
          esc(Number(previousPosition) + 1) + '–' + esc(Number(row.position) - 1) + ' omitted</span></td></tr>';
      }
      var rowClass = row.canada ? ' class="canada"' : '';
      if (isChampionsLeague && Number(row.position) === 9) rowClass = ' class="sports-qualification-cut' + (row.canada ? ' canada' : '') + '"';
      previousPosition = row.position;
      return prefix + '<tr' + rowClass + '><td>' + esc(row.position) + '</td>' +
        '<td>' + clubHtml(row.team, row.logo_url, true) + '</td><td>' + esc(row.played == null ? '–' : row.played) + '</td>' +
        '<td>' + esc(row.points == null ? '–' : row.points) + '</td>' +
        '<td class="sports-gd">' + esc(row.goal_difference == null ? '–' : row.goal_difference) + '</td></tr>';
    }).join('');
    var label = table.label || 'Table';
    if (isChampionsLeague && hasGap) label += ' · leaders + qualification cut';
    var cutNote = isChampionsLeague && rowsData.some(function (row) { return Number(row.position) === 8; }) && rowsData.some(function (row) { return Number(row.position) === 9; })
      ? '<div class="sports-table-note"><span>Top 8</span> qualify directly · <span>9–24</span> enter the knockout playoff</div>'
      : '';
    return '<div class="sports-table-wrap"><div class="sports-table-label">' + esc(label) + '</div>' +
      cutNote + '<table class="sports-table"><thead><tr><th>#</th><th>Team</th><th>P</th><th>Pts</th><th class="sports-gd">GD</th></tr></thead>' +
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
    var commonStage = commonEventStage(event);
    var head = '<div class="sports-event-head"><div class="sports-event-name">' + esc(event.label) + '</div>' +
      (event.event_mode ? '<div class="sports-event-mode">Event edition</div>' : '') + '</div>' +
      (event.source ? '<div class="sports-event-source">Source: ' + esc(event.source) + '</div>' : '') +
      (commonStage ? '<div class="sports-event-stage">' + esc(words(commonStage)) + '</div>' : '');
    if (!event.available) {
      return '<article class="sports-event" data-sports-event="' + esc(event.key) + '">' + head +
        '<div class="sports-event-unavailable">Verified event data is unavailable this morning.</div></article>';
    }
    return '<article class="sports-event" data-sports-event="' + esc(event.key) + '">' + head +
      (event.matches || []).map(function (match) { return eventMatchHtml(match, commonStage); }).join('') +
      eventTableHtml(event.standings, event.key) + highlightsHtml(event.highlights || []) + '</article>';
  }

  function majorEventsHtml(payload) {
    var events = (((payload || {}).major_events || {}).events || []).filter(eventHasContent);
    if (!events.length) return '';
    var eventMode = !!((payload || {}).major_events || {}).event_mode;
    return '<section class="sports-desk sports-events" aria-labelledby="sports-events-title">' +
      sectionHeadHtml('Global board', 'Major Events', eventMode ? 'Tournament edition · the important state, still bounded' : 'Only competitions with something worth knowing this morning', 'sports-events-title') +
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
      sectionHeadHtml('The read', 'Major Headlines', 'Exceptional developments only', 'sports-headlines-title') +
      items.map(majorHeadlineHtml).join('') + '</section>';
  }

  function sportsHtml(payload) {
    var toronto = (payload || {}).toronto || [];
    var torontoHtml = '<section class="sports-desk sports-toronto" aria-labelledby="sports-toronto-title">' +
      sectionHeadHtml('Home teams', 'Toronto', 'Leafs · Raptors · Blue Jays', 'sports-toronto-title') +
      toronto.map(teamRowHtml).join('') + '</section>';
    return torontoHtml + majorEventsHtml(payload) + majorHeadlinesHtml(payload);
  }

  function warmCrestOrigin() {
    if (document.querySelector('link[data-sports-preconnect]')) return;
    var link = document.createElement('link');
    link.rel = 'preconnect';
    link.href = 'https://a.espncdn.com';
    link.crossOrigin = 'anonymous';
    link.setAttribute('data-sports-preconnect', 'true');
    document.head.appendChild(link);
  }

  function renderIfActive() {
    var tab = document.querySelector('.tab.active[data-tab="sports"]');
    var stories = document.getElementById('stories');
    if (!tab || !stories) return;
    stories.innerHTML = sportsHtml(sports);
    stories.setAttribute('data-sports-rendered', 'true');
    settleMarks(stories);
  }

  var sportsTab = document.querySelector('[data-tab="sports"]');
  if (!sportsTab) return;
  sportsTab.addEventListener('pointerenter', warmCrestOrigin, { once: true });
  sportsTab.addEventListener('focus', warmCrestOrigin, { once: true });
  sportsTab.addEventListener('pointerdown', warmCrestOrigin, { once: true });
  sportsTab.addEventListener('click', function () {
    window.setTimeout(renderIfActive, 0);
  });
  renderIfActive();
})();