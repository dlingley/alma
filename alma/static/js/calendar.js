var ending_on = null;
var starting_on = null;
$(document).ready(function(){
    starting_on = $('#id_starting_on').datetimepicker({
        format: "m/d/Y g:i a",
        formatTime: "g:i a",
        scrollMonth: false,
        onShow: function(ct){
            if($('#id_ending_on').val() && ending_on.isValidDate(Date.parseDate($('#id_ending_on').val(), "m/d/Y g:i a"))){
                this.setOptions({
                    maxDate: ending_on.currentTime,
                })
            }
        }
    }).data("xdsoft_datetimepicker").data("xdsoft_datetime");

    // add a datepicker widget to the datetime fields
    ending_on = $('#id_ending_on').datetimepicker({
        format: "m/d/Y g:i a",
        formatTime: "g:i a",
        scrollMonth: false,
        onShow: function(ct){
            if($('#id_starting_on').val() && starting_on.isValidDate(Date.parseDate($('#id_starting_on').val(), "m/d/Y g:i a"))){
                var options = {
                    minDate: starting_on.currentTime,
                }
                if(!$('#id_ending_on').val()){
                    options.value = starting_on.currentTime;
                }
                this.setOptions(options);
            }
        }
    }).data("xdsoft_datetimepicker").data("xdsoft_datetime")

    var end_repeating_on = $('#id_end_repeating_on').datetimepicker({
        format: "m/d/Y",
        scrollMonth: false,
        timepicker: false,
        onShow: function(ct){
            if($('#id_ending_on').val() && ending_on.isValidDate(Date.parseDate($('#id_ending_on').val(), "m/d/Y g:i a"))){
                this.setOptions({
                    minDate: ending_on.currentTime
                })
            }
        }
    })

    // handle toggling the display of the repeating fields on the Request form
    $('#id_repeat').on("change", function(){
        if($(this).prop("checked")){
            $('#repeat-info').show();
        } else {
            $('#repeat-info').hide();
        }
    }).trigger("change");

    // create an event to redraw the display of the calendar
    $('body').on("calendar:redraw", function(e){
        var username = $.trim($('#id_user').val());
        var item = $.trim($('#id_bibs_or_item').val());

        // parse out the username from what they inputted
        username = /\((.*)\)$/.exec(username)
        if(username != null){
            username = username[1];
        }

        // parse out the item id from what they inputted
        item = /\(.*: (.*)\)$/.exec(item)
        if(item != null){
            item = item[1];
        }

        // remove all the indicator classes
        $('.calendar-item').removeClass("user-match item-match unhighlighted");

        // if we have a username or item entered, we need to unhighlight all
        // the requests
        if(username || item){
            $('.calendar-item').addClass("unhighlighted");
        }

        // un-unhighlight anything that matches the username
        if(username){
            $('.calendar-item[data-username="' + username + '"]').addClass("user-match");
        }

        // un-unhighlight anything that matches the item
        if(item){
            $('.calendar-item[data-mms-id="' + item + '"]').addClass("item-match");
        }
    });

    // create an event to reload the calendar
    $('body').on("calendar:reload", function(e, page){
        page = page ? page : 0
        $.get("requests/calendar", {page: page}, function(html){
            $('#calendar-wrapper').html(html);
            $('body').trigger("calendar:redraw");
            $('body').trigger("user-requests:reload");
        });
    });

    // each little RequestInterval object on the calendar has a popover
    $('body').popover({
        "placement": "auto",
        "trigger": "click",
        "selector": '.calendar-item',
        "html": true,
    }).on("show.bs.popover", function(e){
        // ensure only one popover shows at a time
        $("body .calendar-item").not(e.target).popover("destroy");
        $(".popover").remove();
    });

    // handle hiding and showing the delete options on the popover HTML
    $('body').on("change", ".delete-box input[type='checkbox']", function(){
        var el = $(this).closest(".delete-box").find(".show-on-delete");
        if($(this).prop("checked")){
            el.show();
        } else {
            el.hide();
        }
    });

    // when the state in the popover is changed reload the calendar
    $('body').on("change", ".state-toggle", function(){
        var form = $(this).closest("form");
        var url = form.attr('action');
        $.post(url, form.serialize(), function(){
            $('body').trigger("calendar:reload");
        })
    });

    // submit the popover form via ajax
    $('body').on("submit", ".request-interval-form", function(e){
        e.preventDefault();
        var form = $(this);
        var url = form.attr('action');
        $.post(url, form.serialize(), function(){
            $('body').trigger("calendar:reload");
        })
    });

    // whenever the username or item fields change, redraw the calendar to
    // reflect the changes
    $('#id_user, #id_bibs_or_item').on("typeahead:change", function(){
        $('body').trigger("calendar:redraw");
    });

    // when the username changes, fetch the data for the user
    $('#id_user').on("typeahead:change", function(){
        console.log("here");
        $('body').trigger("user-requests:reload");
    });

    // create an event for reloading the user-requests div
    $('body').on("user-requests:reload", function(){
        var username = $('#id_user').val()

        username = /\((.*)\)$/.exec(username)
        if(username != null){
            username = username[1];
        } else {
            username = ""
        }
        if($.trim(username) == ""){
            $('#user-requests').html("");
        } else {
            $.get("/requests/user", {"username": username}, function(html){
                $('#user-requests').html(html);
            });
        }

    });

    // whenever the form changes, check to see if the request is available
    $('form input').on("change", function(){
        $.post("/requests/available", $('form').serialize(), function(data){
            $('#availability').html(data);
        });
    });

    // load the calendar when the page first loads
    $('body').trigger("calendar:reload");

    var hide_or_show_create_request = function(){
        var val = $(this).val();
        if(val.indexOf("MMS_ID") != -1){
            $('#request-section').show();
        } else {
            $('#request-section').hide();
        }
    }

    $('#id_bibs_or_item').typeahead({}, {
        source: function(query, syncResults, asyncResults){
            $.get("/bibs/autocomplete", {query: query}, asyncResults);
        },
        display: function(item){
            return item.name + " (MMS_ID: " + item.mms_id + ")"
        },
        templates: {
            suggestion: function(item){
                return "<div><strong>" + item.name + "</strong></div>"
            }
        },
    },
    {
        source: function(query, syncResults, asyncResults){
            $.get("/items/autocomplete", {query: query}, asyncResults);
        },
        display: function(item){
            return item.name + " (Barcode: " + item.barcode + ")"
        },
        templates: {
            suggestion: function(item){
                return "<div>" + item.name + "<br />#" + item.barcode + "</em></div>"
            }
        },
    }).on("typeahead:change typeahead:select", hide_or_show_create_request)

    $('#id_user').typeahead({}, {
        source: function(query, syncResults, asyncResults){
            $.get("/users/autocomplete", {query: query}, asyncResults);
        },
        display: function(user){
            return user.odin + " (" + user.odin + ")"
        },
        templates: {
            suggestion: function(user){
                return "<div><strong>" + user.odin +  "</strong><br />" + user.full_name + "</div>"
            }
        }
    })
    //.on("typeahead:change", function(){
    //    console.log("here")
    //    console.log($('#id_user').val());
    //    $('body').trigger("calendar:redraw");
    //    console.log($('#id_user').val());
    //})
    //

    $('#request-section').hide();
});
