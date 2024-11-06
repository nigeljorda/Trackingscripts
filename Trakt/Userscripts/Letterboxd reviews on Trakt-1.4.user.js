// ==UserScript==
// @name         Letterboxd reviews on Trakt
// @namespace    http://tampermonkey.net/
// @version      1.4
// @description  Show up to 20 Letterboxd reviews styled like Trakt's own comment section with clickable reviewer names. Adds comment section if missing.
// @match        https://trakt.tv/movies/*
// @grant        GM_xmlhttpRequest
// @require      https://cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/jquery.min.js
// ==/UserScript==

(function() {
    'use strict';

    const maxReviews = 20;

    function fetchMovieUrlAndReviews(callback) {
        let tmdbUrlElement = document.querySelector('a#external-link-tmdb');
        if (!tmdbUrlElement) return;

        let tmdbId = tmdbUrlElement.href.match(/\/movie\/(\d+)/)?.[1];
        if (!tmdbId) return;

        let letterboxdUrl = `https://letterboxd.com/tmdb/${tmdbId}`;
        GM_xmlhttpRequest({
            method: "GET",
            url: letterboxdUrl,
            onload: response => {
                if (response.status === 200) {
                    callback(response.finalUrl);
                }
            }
        });
    }

    function fetchReviewsFromUrl(reviewsUrl, callback) {
        GM_xmlhttpRequest({
            method: "GET",
            url: reviewsUrl,
            onload: response => {
                if (response.status === 200) {
                    let doc = new DOMParser().parseFromString(response.responseText, "text/html");
                    let reviews = Array.from(doc.querySelectorAll('li.film-detail')).map(el => {
                        let content = Array.from(el.querySelectorAll('div.body-text p')).map(p => p.textContent.trim()).join(' ');
                        let username = el.querySelector('a.context strong.name')?.textContent;
                        let profileImageUrl = el.querySelector('a.avatar img')?.src;
                        let rating = el.querySelector('span.rating')?.textContent || 'N/A';
                        let reviewUrl = `https://letterboxd.com${el.querySelector('a.context')?.getAttribute('href')}`;

                        return { content, username, profileImageUrl, rating, reviewUrl };
                    });

                    callback(reviews.filter(r => r.content && r.username && r.profileImageUrl && r.reviewUrl));
                }
            }
        });
    }

    function injectReviewsIntoTrakt(reviews) {
        let targetElement = document.querySelector('#comments');

        // If no comments section exists, create one after the #actors section
        if (!targetElement) {
            let actorsSection = document.querySelector('#actors');
            if (actorsSection) {
                targetElement = $('<div id="comments" class="comments-section"><h2>Comments</h2></div>')[0];
                $(actorsSection).after(targetElement);
            }
        }

        if (targetElement && reviews.length > 0) {
            let reviewSection = $('<div id="letterboxd-reviews"><h3 style="color: #ccc; font-size: 1.2em; font-weight: 600; padding-bottom: 10px; border-bottom: 1px solid #444; margin-bottom: 15px;">Letterboxd Reviews</h3></div>');
            $(targetElement).append(reviewSection);

            reviews.forEach(review => {
                let reviewHtml = `
                    <div class="review" style="display: flex; padding: 15px 10px; border-bottom: 1px solid #444; background-color: #2b2b2b; border-radius: 5px; margin-bottom: 10px;">
                        <div style="margin-right: 10px;">
                            <img src="${review.profileImageUrl}" alt="Profile picture" style="width: 40px; height: 40px; border-radius: 4px;">
                        </div>
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center;">
                                <a href="${review.reviewUrl}" target="_blank" style="color: white; font-weight: bold; font-size: 1em; margin-right: 8px;">${review.username}</a>
                                <span style="color: #aaa; font-size: 0.9em;">Rating: ${review.rating}</span>
                            </div>
                            <p style="color: white; font-size: 0.95em; line-height: 1.4; margin-top: 5px;">${review.content}</p>
                        </div>
                    </div>
                `;
                reviewSection.append(reviewHtml);
            });
        }
    }

    function loadReviews(baseUrl) {
        const pagesToFetch = Math.ceil(maxReviews / 10);
        let uniqueReviews = [];
        let fetchedUrls = new Set();

        function handleNewReviews(reviews) {
            for (let review of reviews) {
                if (uniqueReviews.length >= maxReviews) break;
                if (!fetchedUrls.has(review.reviewUrl)) {
                    uniqueReviews.push(review);
                    fetchedUrls.add(review.reviewUrl);
                }
            }
            if (uniqueReviews.length >= maxReviews) {
                injectReviewsIntoTrakt(uniqueReviews.slice(0, maxReviews));
            }
        }

        for (let page = 1; page <= pagesToFetch && uniqueReviews.length < maxReviews; page++) {
            let reviewsUrl = `${baseUrl}reviews/by/activity${page > 1 ? `/page/${page}` : ''}`;
            fetchReviewsFromUrl(reviewsUrl, handleNewReviews);
        }
    }

    fetchMovieUrlAndReviews(loadReviews);

})();
