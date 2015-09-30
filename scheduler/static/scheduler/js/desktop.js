// desktop specific js



$(document).ready(function() {
    sizeContent();
});


//Every resize of window
$(window).resize(sizeContent);


//Dynamically assign height
function sizeContent() {

     var windowH = $(window).height();
     var contentH = $('#main').height();
     var sideH = $('#side-wrapper').height() + $('#meta-wrapper').height();

     if (contentH < windowH) {
         //$('#main-wrapper').height(windowH);
         $('#main-wrapper').css({'min-height' : windowH});
     }
     else {
         $('#main-wrapper').height("auto");
     }
}
