var SECONDS_PER_PIXEL = 60*60/45.0
var PIXELS_PER_SECOND = 1.0/SECONDS_PER_PIXEL
function positionForTime(unixtime){
    var date = new Date(unixtime*1000);
    var position = date.getHours() * 60 * 60 * PIXELS_PER_SECOND;
    position += date.getMinutes() * 60 * PIXELS_PER_SECOND;
    position += date.getSeconds() * PIXELS_PER_SECOND;
    return position;
}

function positionRequests(requests){
    requests.each(function(i){
        var start_time = parseInt($(this).data("start-time"), 10);
        var end_time = parseInt($(this).data("end-time"), 10);
        var start = positionForTime(start_time);
        var end = positionForTime(end_time);
        var css = {
            "position": "absolute",
            "top": start,
            "height": end-start,
        }
        $(this).css(css);
    });
}

$(document).ready(function(){
    positionRequests($('.request'));
});
