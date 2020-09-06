/* Back to top arrow */
    $(window).scroll(function () {
        if ($(this).scrollTop() >= 50) {
            $('.backtotop').fadeIn(200);
        } else {
            $('.backtotop').fadeOut(200);
        }
    });
    $('.backtotop').click(function (e) {
        e.preventDefault();
        $('body,html').animate({
            scrollTop: 0
        }, 750);
    });
