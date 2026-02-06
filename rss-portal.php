<script>
(function() {
const STYLE = document.createElement('style');
STYLE.textContent = `
#rss-portal {
	margin-inline: auto;
}

/* Pattern
====================================== */
/* .rss-wrapper（flex／横組み）
------------------------------------- */
#rss-portal .rss-wrapper {
	position: relative;
	width: 100%;
}

/* .shelf_pc（SP） */
@media screen and (max-width: 743.9px) {
	#rss-portal .rss-wrapper {
		/* Flex */
		display: flex;
		justify-content: center;
		flex-wrap: wrap;
	}

	#rss-portal .rss-wrapper>:is(li, dd) {
		width: 100%;
	}

	#rss-portal .rss-wrapper>:is(li, dd):nth-of-type(n+2) {
		margin-top: 1rem;
	}
}

/* .shelf（PC） */
@media print,
screen and (min-width: 744px) {
	#rss-portal .rss-wrapper {
		/* Flex */
		display: flex;
		justify-content: space-between;
		flex-wrap: wrap;
	}

	#rss-portal .rss-wrapper:is([data-cols="2"], [data-cols_pc="2"])>:is(li, dd) {
		width: 48.6%;
	}

	#rss-portal .rss-wrapper:is([data-cols="3"], [data-cols_pc="3"])>:is(li, dd) {
		width: 31.5%;
	}

	#rss-portal .rss-wrapper:is([data-cols="2"], [data-cols_pc="2"])>:is(li, dd):nth-of-type(n+3),
	#rss-portal .rss-wrapper:is([data-cols="3"], [data-cols_pc="3"])>:is(li, dd):nth-of-type(n+4) {
		margin-top: 1rem;
	}
}

#rss-portal .rss-slide {
	/* padding  縦  横 */
	padding: calc(var(--⅝fem) * 1) calc(var(--⅝fem) * 1.5);
	border-radius: 0.5rem;
	background: #fff;
}

#rss-portal .rss-title {
	font-size: clamp(1rem, calc(1rem + ((1vw - 0.225rem) * 0.4688)), 1.1375rem);
	font-weight: 500;
}

#rss-portal .rss-meta-fields {
	line-height: 1.11;
	font-size: 0.8125rem;
	color: var(--c-text-400, hsl(223, 6%, 63%));
}

#rss-portal .rss-score {
	padding-block: 0px 1px;
	padding-inline: 0.3em 0.4em;
	border-radius: 0.25rem;
	color: #FFF;
}

#rss-portal .rss-score-1 {
	background: hsl(358, 83%, 53%);
}

#rss-portal .rss-score-2 {
	background: hsl(32, 93%, 53%);
}

#rss-portal .rss-score-3 {
	background: hsl(48, 98%, 53%);
}

#rss-portal .rss-score-4 {
	background: hsl(72, 63%, 53%);
}

#rss-portal .rss-score-5 {
	background: hsl(121, 44%, 53%);
}

#rss-portal .rss-score::before {
	position: relative;
	top: 0px;
	display: inline-flex;
	vertical-align: -0.25em;
	place-content: center;
	place-items: center;
	width: 0.75em;
	font-size: 155.3%;
	font-family: 'Material Symbols Sharp';
	font-variation-settings: 'FILL' 0,
		'wght' 100;
	content: "\\e838";
}

#rss-portal .rss-summary {
	position: relative;
	min-height: 3.6em;
	font-size: 0.7rem;
	color: var(--c-text-600, hsl(223, 6%, 43%));
}

#rss-portal .rss-feedback {
	position: absolute;
	z-index: 10;
	bottom: -0.3rem;
	right: 0;
	margin: auto;
	border-radius: 0.25rem;
	overflow: hidden;
}

#rss-portal .rss-feedback .btn-like,
#rss-portal .rss-feedback .btn-dislike {
	padding-inline: 0.75rem;
	font-size: 12px;
	background: var(--c-base-100, hsl(223, 6%, 93%));
	color: var(--c-text-400, hsl(223, 6%, 63%));
}

/* :hover */
@media (any-hover: hover) {

	#rss-portal .rss-feedback .btn-like:hover,
	#rss-portal .rss-feedback .btn-dislike:hover {
		background: var(--c-base-150, hsl(223, 6%, 89%));
		opacity: 1;
	}
}

#rss-portal .rss-feedback .btn-like::before,
#rss-portal .rss-feedback .btn-dislike::before {
	position: relative;
	top: 0px;
	display: inline-flex;
	vertical-align: -0.35em;
	place-content: center;
	place-items: center;
	width: 0.75em;
	font-size: 173.3%;
	font-family: 'Material Symbols Sharp';
	font-variation-settings: 'FILL' 0,
		'wght' 300;
}

#rss-portal .rss-feedback .btn-like::before {
	left: 0.0625em;
	content: "\\e8dc";
}

#rss-portal .rss-feedback .btn-dislike::before {
	right: 0.0625em;
	content: "\\e8db";
}

#rss-portal .rss-feedback .btn-like.is-liked {
	background: var(--c-linkage-300, hsl(240, 73%, 74%));
	color: #FFF;
}

#rss-portal .rss-feedback .btn-like.is-disliked {
	background: var(--c-error-300, hsl(352, 99%, 74%));
	color: #FFF;
}
`;
document.getElementsByTagName('head')[0].appendChild(STYLE);
})();
</script>

<div id="rss-portal" class="rss-container">
  <div id="rss-loading">読み込み中...</div>
  <ul id="rss-wrapper" class="rss-wrapper" data-cols_pc="2"></ul>
</div>

<script>
  (function() {
    const RSS_API_URL = '/api/rss-portal';

    // ローカルストレージから非表示リストを取得
    function getHiddenArticles() {
      try {
        const hidden = localStorage.getItem('rss-portal-hidden');
        return hidden ? JSON.parse(hidden) : [];
      } catch (e) {
        localStorage.removeItem('rss-portal-hidden');
        return [];
      }
    }

    // 記事を非表示リストに追加
    function hideArticle(articleId) {
      const hidden = getHiddenArticles();
      if (!hidden.includes(articleId)) {
        hidden.push(articleId);
        localStorage.setItem('rss-portal-hidden', JSON.stringify(hidden));
      }
    }

    // Likeした記事を記録
    function getLikedArticles() {
      try {
        const liked = localStorage.getItem('rss-portal-liked');
        return liked ? JSON.parse(liked) : [];
      } catch (e) {
        localStorage.removeItem('rss-portal-liked');
        return [];
      }
    }

    function markAsLiked(articleId) {
      const liked = getLikedArticles();
      if (!liked.includes(articleId)) {
        liked.push(articleId);
        localStorage.setItem('rss-portal-liked', JSON.stringify(liked));
      }
    }

    fetch(RSS_API_URL + '/articles')
      .then(res => {
        if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
        return res.json();
      })
      .then(data => {
        document.getElementById('rss-loading').style.display = 'none';
        const wrapper = document.getElementById('rss-wrapper');
        const hiddenArticles = getHiddenArticles();
        const likedArticles = getLikedArticles();

<?php if (is_front_page()): ?>
          //最大10件まで
          const maxArticles = 10;
          data.articles.slice(0, maxArticles).forEach(article => {
<?php else: ?>
          data.articles.forEach(article => {
<?php endif; ?>

          // 非表示リストにある記事はスキップ
          if (hiddenArticles.includes(article.id)) {
            return;
          }

          const isLiked = likedArticles.includes(article.id);
          const rssDate = new Date(article.published_at).toISOString().split('T')[0];

          const li = document.createElement('li');
          li.className = 'rss-slide';
          li.id = 'article-' + article.id;

          const h4 = document.createElement('h4');
          h4.className = 'rss-title';
          const titleLink = document.createElement('a');
          titleLink.href = article.link;
          titleLink.target = '_blank';
          titleLink.textContent = article.title;
          titleLink.addEventListener('click', function() { trackClick(article.id); });
          h4.appendChild(titleLink);

          const metaDiv = document.createElement('div');
          metaDiv.className = 'rss-meta-fields';
          const timeEl = document.createElement('time');
          timeEl.className = 'rss-date';
          timeEl.setAttribute('datetime', article.published_at);
          timeEl.textContent = rssDate;
          const feedSpan = document.createElement('span');
          feedSpan.className = 'rss-feedname';
          feedSpan.textContent = article.feed_name;
          const scoreSpan = document.createElement('span');
          scoreSpan.className = 'rss-score rss-score-' + article.score;
          scoreSpan.textContent = article.score;
          metaDiv.appendChild(timeEl);
          metaDiv.appendChild(document.createTextNode(' | '));
          metaDiv.appendChild(feedSpan);
          metaDiv.appendChild(document.createTextNode(' '));
          metaDiv.appendChild(scoreSpan);

          const summaryP = document.createElement('p');
          summaryP.className = 'rss-summary';
          summaryP.appendChild(document.createTextNode(article.summary || ''));
          const feedbackLabel = document.createElement('label');
          feedbackLabel.className = 'rss-feedback';
          const btnLike = document.createElement('a');
          btnLike.className = 'btn-like' + (isLiked ? ' is-liked' : '');
          btnLike.textContent = isLiked ? '' : '';
          btnLike.addEventListener('click', function() { sendFeedback(article.id, 'like', this); });
          const btnDislike = document.createElement('a');
          btnDislike.className = 'btn-dislike';
          btnDislike.textContent = '';
          btnDislike.addEventListener('click', function() { sendFeedback(article.id, 'dislike', this); });
          feedbackLabel.appendChild(btnLike);
          feedbackLabel.appendChild(btnDislike);
          summaryP.appendChild(feedbackLabel);

          li.appendChild(h4);
          li.appendChild(metaDiv);
          li.appendChild(summaryP);
          wrapper.appendChild(li);
        });
      })
      .catch(err => {
        document.getElementById('rss-loading').textContent = 'エラーが発生しました';
        console.error(err);
      });
  })();

  //クリック追跡関数
  function trackClick(articleId) {
    fetch('/api/rss-portal/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        article_id: articleId,
        feedback: 'click'
      })
    });
    //return true でリンク遷移を妨げない
  }

  function sendFeedback(articleId, type, button) {
    // 楽観的UI更新の前の状態を保存
    const prevButtonClass = button.className;
    const prevButtonText = button.textContent;

    fetch('/api/rss-portal/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        article_id: articleId,
        feedback: type
      })
    }).then(res => {
      if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
      if (type === 'like') {
        // Likeの場合：ボタンの見た目を変更
        const likedList = getLikedArticles();
        if (!likedList.includes(articleId)) {
          likedList.push(articleId);
          localStorage.setItem('rss-portal-liked', JSON.stringify(likedList));
        }
        button.classList.add('is-liked');
        button.textContent = '';
      } else {
        // Dislikeの場合：記事を非表示にして、ローカルストレージに記録
        const hiddenList = getHiddenArticles();
        if (!hiddenList.includes(articleId)) {
          hiddenList.push(articleId);
          localStorage.setItem('rss-portal-hidden', JSON.stringify(hiddenList));
        }
        // 記事をフェードアウトして削除
        const articleDiv = document.getElementById('article-' + articleId);
        if (articleDiv) {
          articleDiv.style.transition = 'opacity 0.3s';
          articleDiv.style.opacity = '0';
          setTimeout(() => articleDiv.remove(), 300);
        }
      }
    }).catch(err => {
      console.error('Feedback failed:', err);
      // UIを元に戻す
      button.className = prevButtonClass;
      button.textContent = prevButtonText;
      // Dislikeで非表示にした場合の復元
      if (type === 'dislike') {
        const articleDiv = document.getElementById('article-' + articleId);
        if (articleDiv) {
          articleDiv.style.opacity = '1';
        }
      }
      // localStorage からも取り消す
      if (type === 'like') {
        const likedList = getLikedArticles().filter(id => id !== articleId);
        localStorage.setItem('rss-portal-liked', JSON.stringify(likedList));
      } else {
        const hiddenList = getHiddenArticles().filter(id => id !== articleId);
        localStorage.setItem('rss-portal-hidden', JSON.stringify(hiddenList));
      }
    });
  }
</script>