/*jslint browser: true, plusplus: true, scripturl: true */
/*global jQuery, Handlebars, moment, confirm */

var PanoptoScheduler = (function ($) {
    "use strict";

    var term_lookahead = 2;

    // prep for api post/put
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    function search_in_progress(selector) {
        var tpl = Handlebars.compile($("#ajax-waiting").html());
        $(selector).html(tpl());
    }

    function course_search_in_progress() {
        $("form.course-search button").attr('disabled', 'disabled');
        search_in_progress(".course-search-result");
    }

    function event_search_in_progress() {
        $("form.event-search button").attr('disabled', 'disabled');
        search_in_progress(".event-search-result");
    }

    function recorder_select_in_progress() {
        search_in_progress(".recorder-select-result");
    }

    function course_search_complete() {
        $("form.course-search button").removeAttr('disabled');
    }

    function event_search_complete() {
        $("form.event-search button").removeAttr('disabled');
    }

    function room_search_complete() {
        $('.rooms-loading').remove();
    }

    function recorder_search_complete() {
        $('.recorders-loading').hide();
    }

    function panopto_folder_search_complete() {
        $('.folder-picker .result .loading').addClass('hidden');
    }

    function panopto_event(node) {
        var recording_node = (node.hasClass('btn-group')) ? node : null;

        if (!recording_node) {
            recording_node = node.closest('.btn-group');
        }

        if (!recording_node) {
            recording_node = node.find('.btn-group');
        }

        return window.scheduler.events[recording_node.attr('data-schedule-key')];
    }

    function button_loading(node) {
        var cluster = node.closest('.schedule-button-cluster'),
            pe = panopto_event(node),
            btngrp = cluster.find('.btn-group');

        if (pe && pe.slider) {
            pe.slider.slider('disable');
        }

        btngrp.find('button, input').attr('disabled', 'disabled');
        $('.loading', cluster).show();
    }

    function button_stop_loading(node) {
        var cluster = node.closest('.schedule-button-cluster'),
            pe = panopto_event(node),
            btngrp = cluster.find('.btn-group');

        if (pe && pe.slider) {
            pe.slider.slider('enable');
        }

        $('.loading', cluster).hide();
        btngrp.find('button, input').removeAttr('disabled');
    }

    function panopto_api_path(service, params) {
        var url = '/scheduler/',
            query;

        if (window.scheduler.hasOwnProperty('blti')) {
            url += 'blti/';
        }

        url += 'api/v1/' + service;

        if (params) {
            query = [];
            $.each(params, function (k, v) {
                query.push(k + '=' + encodeURIComponent(v));
            });
            url += '?' + query.join('&');
        }

        return url;
    }

    function panopto_folder_url(panopto_folder_id) {
        return 'http://' + window.scheduler.panopto_server +
            '/Panopto/Pages/Sessions/List.aspx#folderID=%22' +
            panopto_folder_id  + '%22&status=%5B4%2C0%2C5%2C3%2C2%2C1%5D';
    }

    function panopto_recording_url(panopto_recording_id) {
        return 'http://' + window.scheduler.panopto_server +
            '/Panopto/Pages/Viewer.aspx?id=' +
            panopto_recording_id;
    }

    function panopto_recording_length(start, stop) {
        return moment(start).format('h:mm a') + '-' + moment(stop).format('h:mm a');
    }

    function panopto_full_duration(panopto_event) {
        return (moment(panopto_event.recording.start).isSameOrBefore(panopto_event.event.start) &&
                moment(panopto_event.recording.end).isSameOrAfter(panopto_event.event.end));
    }

    function panopto_can_record(panopto_event) {
        var now = _now();

        return (panopto_event.recording.recorder_id &&
                now.isAfter(moment(panopto_event.event.start)) &&
                now.isBefore(moment(panopto_event.event.end)));
    }

    function panopto_is_recording(panopto_event) {
        var now = _now();

        return (panopto_event.recording.recorder_id &&
                panopto_event.recording.id &&
                now.isAfter(moment(panopto_event.recording.start)) &&
                now.isBefore(moment(panopto_event.recording.end)));
    }

    function panopto_is_recorded(panopto_event) {
        var now = _now();

        return (panopto_event.recording.id &&
                now.isAfter(moment(panopto_event.recording.end)));
    }

    function failure_modal(title, default_text, xhr) {
        var tpl = Handlebars.compile($('#ajax-fail-tmpl').html()),
            modal_container,
            failure_text = default_text,
            err;

        if (xhr && xhr.hasOwnProperty('responseText')) {
            try {
                err = JSON.parse(xhr.responseText);

                if (err.hasOwnProperty('error')) {
                    failure_text = err.error;
                }
            } catch (ignore) {
            }
        }

        $('body').append(tpl({
            failure_title: title,
            failure_message: failure_text,
            full_failure_message: xhr ? xhr.responseText : ''
        }));

        modal_container = $('#failure-modal');
        modal_container.modal();
        modal_container.on('hidden.bs.modal', function (e) {
            $(e.target).remove();
        });

        return modal_container;
    }

    function update_schedule_buttons(event) {
        var schedule_cluster,
            button_group,
            event_search = false,
            folder_url = null,
            now,
            recordable,
            recorded = false,
            tpl;

        if (event) {
            now = _now();
            recordable = (now.isAfter(moment(event.event.start)) &&
                          now.isBefore(moment(event.event.end)));
            button_group = $('.btn-group[data-schedule-key="' + event.key + '"]');
            schedule_cluster = button_group.closest('.schedule-button-cluster');
            event_search = (schedule_cluster.parents('div.event-search').length > 0);
            if (event_search && event.recording.id) {
                if (event.recording.folder.id) {
                    folder_url = panopto_folder_url(event.recording.folder.id);
                } else {
                    $.ajax({
                        type: 'GET',
                        url: panopto_api_path('session/' + event.recording.id),
                        async: false
                    })
                        .done(function (msg) {
                            tpl = Handlebars.compile($('#folder_created_message').html());
                            folder_url = panopto_folder_url(msg.folder_id);
                            failure_modal('Panopto Folder Created',
                                          tpl({folder_url: folder_url}),
                                          {});

                        });
                }
            }

            schedule_cluster.find('.loading').hide();

            if (event.recording.id) {
                button_group.removeClass('unscheduled');
                button_group.removeClass('can-record');
                if (recordable) {
                    button_group.removeClass('scheduled');
                    if (now.isAfter(event.recording.end)) {
                        button_group.removeClass('is_recording');
                        button_group.addClass('is_recorded');
                        $('button', button_group).attr('disabled', 'disabled');
                        recorded = true;
                    } else {
                        button_group.addClass('is_recording');
                    }
                } else {
                    button_group.removeClass('is_recording');
                    button_group.addClass('scheduled');
                }

                if (event.recording.is_broadcast && !recorded) {
                    schedule_cluster.addClass('is-webcast');
                } else {
                    schedule_cluster.removeClass('is-webcast');
                }

                if (event.recording.is_public && !recorded) {
                    schedule_cluster.addClass('is-public');
                } else {
                    schedule_cluster.removeClass('is-public');
                }

                if (panopto_full_duration(event) || recorded) {
                    schedule_cluster.removeClass('partial-duration');
                } else {
                    schedule_cluster.addClass('partial-duration');
                    tpl = panopto_recording_length(event.recording.start,
                                                   event.recording.end);
                    schedule_cluster.find('.schedule-duration span').html(tpl);
                }
            } else {
                schedule_cluster.removeClass('is-public');
                schedule_cluster.removeClass('is-webcast');
                schedule_cluster.removeClass('partial-duration');
                button_group.removeClass('scheduled');
                button_group.removeClass('is_recording');

                if (recordable) {
                    button_group.removeClass('unscheduled');
                    button_group.addClass('can-record');
                } else {
                    button_group.removeClass('can-record');
                    button_group.addClass('unscheduled');
                }
            }
        }

        if ($('.list-group .btn-group.unscheduled button').not(':disabled').length) {
            $('.batchswitch button').removeAttr('disabled');
        } else {
            $('.batchswitch button').attr('disabled', 'disabled');
        }
    }

    function paint_course_schedule(course, events) {
        /*jshint validthis: true */
        var tpl = Handlebars.compile($('#course-search-result-template').html()),
            joint = null,
            panopto_folder_id = null,
            canvas_course_id = null,
            future_meetings = false,
            context = {
                course: course.name,
                course_id: course.canvas_id,
                joint: null,
                rooms: [],
                single_room: true,
                term: course.term,
                has_recorder: false,
                unscheduled: false,
                full_duration: true,
                schedule: []
            };

        window.scheduler.events = {};

        $.each(events, function () {
            var event_start_date,
                event_end_date,
                now,
                in_the_past;

            if (this.profile.toLowerCase() === 'final') {
                return true;
            }

            event_start_date = moment(this.event.start);
            event_end_date = moment(this.event.end);
            now = _now();
            in_the_past = event_end_date.isBefore(now);

            if (!in_the_past && !future_meetings) {
                future_meetings = true;
            }

            window.scheduler.events[this.key] = this;

            if (!context.has_recorder) {
                context.has_recorder = (this.recording.recorder_id !== null);
            }

            if (context.has_recorder && !context.unscheduled) {
                context.unscheduled = (this.recording.id === null);
            }

            if (!panopto_folder_id) {
                panopto_folder_id = this.recording.folder.id;
            }

            if (!canvas_course_id) {
                canvas_course_id = this.recording.folder.external_id;
            }

            if (!joint) {
                joint = (this.joint) ? this.joint.join(', ') :  '';
            }

            if (this.space.name && context.rooms.indexOf(this.space.name) < 0) {
                context.rooms.push(this.space.name);
            }

            context.schedule.push({
                key: this.key,
                month_num: event_start_date.format('M'),
                day: event_start_date.format('D'),
                weekday: event_start_date.format('ddd'),
                event_start_time: event_start_date.format('h:mm'),
                event_end_time: event_end_date.format('h:mm'),
                ampm: event_end_date.format('a'),
                course: course.name,
                name: this.space.name,
                name_index: (this.space.name) ? context.rooms.indexOf(this.space.name) : null,
                space_id: this.space.id,
                contact: this.contact.hasOwnProperty('name') ? this.contact.name : null,
                contact_email: this.contact.hasOwnProperty('email') ? this.contact.email : null,
                recording_name: this.recording.name,
                recording_id: this.recording.id,
                recording_is_broadcast: this.recording.is_broadcast,
                recording_is_public: this.recording.is_public,
                full_duration: panopto_full_duration(this),
                recording_time: panopto_recording_length(this.recording.start,
                                                         this.recording.end),
                recorder_id: this.recording.recorder_id,
                event_search: false,
                folder_url: (this.recording.folder.id) ?
                    panopto_folder_url(this.recording.folder.id) : null,
                in_the_past: in_the_past,
                can_record: panopto_can_record(this),
                is_recording: panopto_is_recording(this),
                is_recorded: panopto_is_recorded(this),
                schedulable: this.schedulable,
                disabled: (this.schedulable &&
                    ((this.recording.id && now.isBefore(this.recording.end)) ||
                        (!this.recording.id && this.recording.recorder_id)) &&
                            event_end_date.isAfter(now)) ? '' : 'disabled',
                has_recorder: context.has_recorder
            });
        });

        if (joint && joint.length) {
            context.joint = joint;
        }

        context.single_room = (context.rooms.length === 1);

        context.future_meetings = future_meetings;

        context.sws_section_url = '/restclients/view/sws/student/v5/course/' +
            course.sws_label + '.json';

        if (panopto_folder_id) {
            context.panopto_folder_url = panopto_folder_url(panopto_folder_id);
        }

        if (canvas_course_id) {
            context.canvas_course_url = window.scheduler.canvas_host +
                '/courses/' + canvas_course_id;
        }

        $('.course-search-result').html(tpl(context));
        update_schedule_buttons();
        //$('.xlist-icon').popover({ trigger: 'hover' });
    }

    function event_context(event) {
        var event_start_date = moment(event.event.start),
            event_end_date = moment(event.event.end),
            now = _now();

        return {
            key: event.key,
            canvas_host: window.scheduler.canvas_host,
            month_num: event_start_date.format('M'),
            day: event_start_date.format('D'),
            year: event_start_date.format('YY'),
            weekday: event_start_date.format('ddd'),
            event_start_time: event_start_date.format('h:mm'),
            event_end_time: event_end_date.format('h:mm'),
            ampm: event_end_date.format('a'),
            name: ($.isArray(event.name)) ? event.name : [event.name],
            contact: event.contact.hasOwnProperty('name') ? event.contact.name : null,
            contact_email: event.contact.hasOwnProperty('email') ? event.contact.email : null,
            contact_netids: (event.contact.hasOwnProperty('loginid') && event.contact.loginid && event.contact.loginid.length) ?
                [event.contact.loginid] : [],
            recording_name: event.recording.name,
            recording_is_broadcast: event.recording.is_broadcast,
            recording_is_public: event.recording.is_public,
            full_duration: panopto_full_duration(event),
            recording_time: panopto_recording_length(event.recording.start,
                                                     event.recording.end),
            recording_id: event.recording.id,
            recorder_id: event.recording.recorder_id,
            recording_url: event.recording.id ?
                panopto_recording_url(event.recording.id) : null,
            event_search: true,
            folder_name: event.recording.folder.name,
            folder_id: event.recording.folder.id,
            folder_external_id: event.recording.folder.external_id,
            folder_url: (event.recording.folder.id) ?
                panopto_folder_url(event.recording.folder.id) : null,
            creator_netids: (event.recording.folder.auth &&
                             event.recording.folder.auth.hasOwnProperty('creators') &&
                             event.recording.folder.auth.creators) ?
                event.recording.folder.auth.creators : [],
            scheduler_link: scheduler_link_from_external_id(event.recording.external_id),
            in_the_past: false,
            can_record: panopto_can_record(event),
            is_recording: panopto_is_recording(event),
            is_recorded: panopto_is_recorded(event),
            disabled: (event.schedulable &&
                (event.recording.id || event.recording.recorder_id) &&
                event_end_date.isAfter(now)) ? '' : 'disabled',
            has_recorder: true
        };
    }

    function scheduler_link_from_external_id(external_id) {
        var parts = (external_id) ? external_id.split('-') : null;

        if (parts && parts.length === 8) {
            return '/courses/?course=' + parts[0] + '-' + parts[1] +
                '-' + encodeURIComponent(parts[2]) + '-' +
                parts[3] + '-' + parts[4];
        }

        return null;
    }

    function paint_space_schedule(events) {
        /*jshint validthis: true */
        var tpl = Handlebars.compile($('#event-search-result-template').html()),
            context = {
                has_recorder: true,
                room: $('select#room-select option:selected').text(),
                unscheduled: false,
                search_date: moment($('input#calendar.input-date').val()).format('MMMM D, YYYY'),
                schedule: []
            };

        window.scheduler.events = {};

        $.each(events, function () {
            if (this.profile.toLowerCase() !== 'final') {
                window.scheduler.events[this.key] = this;
                if (!context.unscheduled) {
                    context.unscheduled = (this.recording.id === null);
                }

                context.schedule.push(event_context(this));
            }
        });

        $('.event-search-result').html(tpl(context));
        if (context.schedule.length) {
            update_schedule_buttons();
        }
    }

    function update_history_state(search_param) {
        history.pushState({}, '', search_param);
    }

    function course_search_failure(xhr) {
        var html = $('#course-search-failure').html();

        failure_modal('Course schedule could not be found',
                      'Make sure the search terms are correct, and try again.',
                      xhr);

        $(".course-search-result").html(html ? Handlebars.compile(html)() : '');
    }

    function event_search_failure(xhr) {
        $(".event-search-result").empty();
        failure_modal('Event Search Failure',
                      'Please try again later.',
                      xhr);
    }

    function validate_login_ids_failure(xhr) {
        failure_modal('Error validating login ids',
                      'Please try again.',
                      xhr);
    }

    function recorder_select_failure(xhr) {
        $(".event-search-result").empty();
        failure_modal('Recorder Search Failure',
                      'Please try again later.',
                      xhr);
    }

    function set_course_search_criteria(course) {
        $('input#curriculum').val(course ? course.curriculum : '');
        $('input#course-code').val(course ? course.number : '');
        $('input#section').val(course ? course.section : '');
    }

    function find_course(course) {
        $.ajax({
            type: 'GET',
            url: panopto_api_path('schedule/' + course.canvas_id),
            waitIndicatator: course_search_in_progress,
            complete: course_search_complete
        })
            .fail(course_search_failure)
            .done(function (msg) {
                paint_course_schedule(course, msg);
                set_course_search_criteria();
            });
    }

    function do_course_search(ev) {
        var course = {
                term: $('select#qtr-select').val().trim().toLowerCase()
            },
            parts = course.term.split('-');

        parts.push($('input#curriculum').val().trim().toUpperCase());
        parts.push($('input#course-code').val().trim());
        parts.push($('input#section').val().trim().toUpperCase());

        course.name = parts.slice(2, 5).join(' ');
        course.canvas_id = parts.join('-');
        course.sws_label = parts.slice(0, 4).join(',') + '/' + parts.slice(-1);

        if (ev) {
            ev.preventDefault();
        }

        update_history_state('?course=' + course.canvas_id);
        find_course(course);
    }

    function do_event_search(ev) {
        var recorder_val = $('select#room-select option:selected').val(),
            ids = recorder_val.split('|'),
            day_val = $('input#calendar.input-date').val();

        ev.preventDefault();
        update_history_state('?events=' + ids[0] +
            '|' + ids[1] + '|' + day_val.split('/').join('-'));
        search_events_in_space(ids[0], ids[1], day_val);
    }

    function search_events_in_space(space_id, recorder_id, date) {
        $.ajax({
            type: 'GET',
            url: panopto_api_path('schedule/', {
                space_id: space_id,
                start_dt: moment(date).toISOString(),
                recorder_id: recorder_id
            }),
            waitIndicatator: event_search_in_progress,
            complete: event_search_complete
        })
            .fail(event_search_failure)
            .done(function (msg) {
                paint_space_schedule(msg);
            });
    }

    function find_course_from_search(raw) {
        var search = raw.match('^[?]course=(.*)$'),
            course,
            term;

        if (search) {
            course = parse_sis_id(decodeURIComponent(search[1]));
            if (course) {
                term = $('select#qtr-select option[value="' + course.term + '"]');
                term.prop('selected', true);
                set_course_search_criteria(course);
                find_course(course);
                return true;
            }
        }

        return false;
    }

    function update_event_search_criteria(space_id, recorder_id, date) {
        var select = $('select#room-select');

        $('#date-picker').datepicker('setDate', moment(date, 'MM-DD-YYYY').toDate());
        select.one('scheduler.recorders_loaded', function () {
            select.val(space_id + '|' + recorder_id);
        });
    }

    function find_event_from_search(raw) {
        var search = raw.match('^\\?events=\(\\\d{4}\)\\\|\([a-f-\\\d]+\)\\\|\(\(\\\d{1,2}-\){2}\\\d{4}\)$');

        if (search) {
            update_event_search_criteria(search[1], search[2], search[3]);
            search_events_in_space(search[1], search[2], search[3]);
            return true;
        }

        return false;
    }

    function do_scheduled_recording_search(session_ids) {
        $.ajax({
            type: 'POST',
            url: panopto_api_path('schedule/'),
            contentType: 'application/json',
            data: JSON.stringify({
                session_ids: session_ids
            }),
            waitIndicatator: event_search_in_progress,
            complete: event_search_complete
        })
            .fail(event_search_failure)
            .done(function (msg) {
                paint_space_schedule(msg);
            });
    }

    function update_term_selector() {
        /*jshint validthis: true */
        $('#selected-quarter').html($("option:selected", this).text());
    }

    function init_term_selector() {
        var quarters = ['winter', 'spring', 'summer', 'autumn'],
            year,
            i,
            j,
            s,
            t,
            opt;

        if (!$("select#qtr-select").length) {
            return;
        }

        year = window.scheduler.term.year;
        j = quarters.indexOf(window.scheduler.term.quarter.toLowerCase());
        for (i = 0; i < term_lookahead; i += 1) {
            s = quarters[j];
            t = s[0].toUpperCase() + s.slice(1) + ' ' + year;

            opt = $('<option></option>')
                    .text(t)
                    .attr('value', year + '-' + s)
                    .attr('title', 'Select ' + t)
                    .prop("selected", (i === 0) ? true : false);

            $("select#qtr-select").append(opt);

            if (++j >= quarters.length) {
                j = 0;
                year++;
            }
        }
        $("select#qtr-select").change(update_term_selector);
    }

    function init_date_picker() {
        var picker = $('#date-picker'),
            start_date = _now().format('M/D/YYYY');

        if (picker.length) {
            $('input', picker).val(start_date);
            picker.datepicker({
                format: 'm/d/yyyy',
                startDate: start_date,
                toggleActive: false,
                todayHighlight: true
            });
        }
    }

    function init_room_select(recorders) {
        var select = $('select#room-select');

        $.each(recorders, function () {
            select.append($('<option></option>')
                              .text(this.name)
                              .attr('value', this.external_id + '|' + this.id)
                              .attr('title', 'room ' + this.name));
        });

        select.trigger('scheduler.recorders_loaded');
    }

    function init_event_search() {
        $.ajax({
            type: 'GET',
            url: panopto_api_path('recorder/'),
            complete: room_search_complete
        })
            .fail(event_search_failure)
            .done(init_room_select);
    }

    function init_recorder_search() {
        $.ajax({
            type: 'GET',
            url: panopto_api_path('recorder/', { timeout: 0 }),
            complete: recorder_search_complete
        })
            .fail(recorder_select_failure)
            .done(init_room_select);
        Handlebars.registerPartial('reservation-list', $('#reservation-list-partial').html());
    }

    function disable_event_scheduler(pe) {
        var $settings = $('.reservation-settings');

        $settings.find('input, select, button').attr('disabled', true);
        $settings.find('a').addClass('inactivate');
        if (pe && pe.slider) {
            pe.slider.slider('disable');
        }
    }

    function disable_event_schedule_button() {
        $("button.schedule-event").attr('disabled', 'disabled');
    }

    function enable_event_schedule_button() {
        $("button.schedule-event").removeAttr('disabled');
    }

    function enable_event_scheduler(pe) {
        var $settings = $('.reservation-settings');

        $settings.find('input, select, button').removeAttr('disabled');
        $settings.find('a').removeClass('inactivate');
        if (pe && pe.slider) {
            pe.slider.slider('enable');
        }
    }

    function gather_event_recording($node, pe) {
        var changes = panopto_schedule_change(pe, $node),
            folder_name = $node.find('.foldername .field a').text(),
            fields = ['foldername', 'creators'],
            creators = [],
            $field,
            $input,
            start,
            now,
            i;

        if (changes && changes.schedule) {
            now = _now();
            start = moment.unix(changes.schedule.start);

            if (start.isBefore(now)) {
                start = now;
            }

            pe.recording.start = start.toISOString();
            pe.recording.end = moment.unix(changes.schedule.end).toISOString();

        }

        pe.recording.is_public = ($node.find('[name^=public_]:checked').val() === '1');

        if (changes && changes.webcast) {
            pe.recording.is_broadcast = changes.webcast.value;
        }

        pe.recording.folder.external_id = '';
        if ($('.foldername .field a').text() === $('.foldername input.original-folder').val()) {
            pe.recording.folder.id = $('.foldername input.original-folder-id').val();
        } else {
            pe.recording.folder.id = '';
        }
/*
        for (i = 0; i < fields.length; i += 1) {
            $field = $node.find('.' + fields[i] + ' .form-group');
            if (!$field.hasClass('hidden')) {
                panopto_event_field_editor_input_finish($field.find('input'));
            }
        }
*/
/*
        $node.find('ul li').each(function () {
            var $li = $(this);

            if ($li.is(':visible') && !$li.hasClass('placeholder')) {
                creators.push($li.text());
            }
        });

        pe.recording.folder.creators = creators;
*/

        if (!pe.recording.folder.name || (pe.recording.folder.name !== folder_name)) {
            pe.recording.folder.name = folder_name;
            pe.recording.folder_id = null;
        }

        return pe;
    }

    function schedule_panopto_event_recording(e) {
        var $node = $('.reservation-settings[data-schedule-key]'),
            key = $node.attr('data-schedule-key'),
            pe = gather_event_recording($node, window.scheduler.events[key]);

        e.preventDefault();
        e.stopPropagation();

        if (!pe) {
            return;
        }

        disable_event_scheduler();

        schedule_panopto_recording(pe);
    }

    function unschedule_panopto_event_recording(e) {
        /*jshint validthis: true */
        var $node = $('.reservation-settings[data-schedule-key]'),
            key = $node.attr('data-schedule-key'),
            pe = gather_event_recording($node, window.scheduler.events[key]);

        e.preventDefault();
        e.stopPropagation();

        if (!pe) {
            return;
        }

        disable_event_scheduler();
        confirm_unschedule_event(pe, $(this));
    }

    function modify_panopto_event_recording(e) {
        var $node = $('.reservation-settings[data-schedule-key]'),
            key = $node.attr('data-schedule-key'),
            pe = gather_event_recording($node, window.scheduler.events[key]);

        e.preventDefault();
        e.stopPropagation();

        if (!pe) {
            return;
        }

        disable_event_scheduler(pe);
        modify_panopto_recording(pe);
    }

    function schedule_panopto_course_recording(panopto_event) {
        var $btngrp = $('[data-schedule-key="' + panopto_event.key + '"]'),
            $button = $btngrp.find('> button:first-child');

        $btngrp.on('scheduler.set_schedule_start', function () {
            button_loading($button);
        });

        $btngrp.one('scheduler.set_schedule_finish', function () {
            button_stop_loading($button);
            update_schedule_buttons(panopto_event);
        });

        schedule_panopto_recording(panopto_event);
    }

    function schedule_panopto_recording(panopto_event) {
        if (panopto_event.recording.id) {
            return;
        }

        modify_panopto_recording(panopto_event, 'POST');
    }

    function modify_panopto_recording(panopto_event, method) {
        var start_time = moment(panopto_event.recording.start),
            end_time = moment(panopto_event.recording.end),
            now = _now(),
            request_data = {
                key: panopto_event.key,
                name: panopto_event.recording.name,
                external_id: panopto_event.recording.external_id,
                recording_id: panopto_event.recording.id,
                recorder_id: panopto_event.recording.recorder_id,
                folder_name: panopto_event.recording.folder.name,
                folder_id: panopto_event.recording.folder.id,
                folder_external_id: panopto_event.recording.folder.external_id,
                creators: panopto_event.recording.folder.creators,
                start_time: panopto_event.recording.start,
                end_time: panopto_event.recording.end,
                event_start: panopto_event.event.start,
                event_end: panopto_event.event.end,
                is_broadcast: panopto_event.recording.is_broadcast,
                is_public: panopto_event.recording.is_public
            },
            $initiator = $('[data-schedule-key="' + panopto_event.key + '"]');

        if (!method) {
            method = 'PUT';
        }

        if (panopto_event.contact.hasOwnProperty('loginid') && panopto_event.contact.loginid) {
            request_data.loginid = panopto_event.contact.loginid;
        }

        if (now.isAfter(end_time)) {
            failure_modal('Cannot Set Recording Time',
                          'Records must be scheduled for future dates.',
                          {});
            return;
        }

        if (now.isAfter(start_time)) {
            panopto_event.recording.start = now.toISOString();
            request_data.start_time = panopto_event.recording.start;
        }

        $initiator.trigger('scheduler.set_schedule_start');

        $.ajax({
            type: method,
            url: panopto_api_path('session/'),
            processData: false,
            contentType: 'application/json',
            data: JSON.stringify(request_data)
        }).done(function (data) {
            if (data.hasOwnProperty('recording_id')) {
                panopto_event.recording.id = data.recording_id;
            }
            if (data.hasOwnProperty('messages') &&
                $.isArray(data.messages) &&
                data.messages.length) {
                panopto_event.create_messages = data.messages;
            }
        }).fail(function (xhr) {
            if (xhr.status === 409) {
                var response = JSON.parse(xhr.responseText),
                    format = 'h:mm a';

                failure_modal('Cannot Schedule Recording',
                              'This request conflicts with<p style="text-align: center;">' +
                              response.conflict_name +
                              '</p>scheduled from ' +
                              moment(response.conflict_start).format(format) +
                              ' until ' +
                              moment(response.conflict_end).format(format),
                              {});
            } else {
                failure_modal('Cannot Schedule Recording',
                              'Please try again later.',
                              xhr);
            }
        }).always(function () {
            $initiator.trigger('scheduler.set_schedule_finish');
        });
    }

    function remove_scheduled_panopto_recording(panopto_event, button) {
        var now = _now();

        // delete only scheduled (future) recordings
        if (!(panopto_event.recording.id && now.isBefore(panopto_event.recording.start))) {
            return;
        }

        button.trigger('scheduler.remove_schedule_start', [panopto_event]);

        $.ajax({
            type: 'DELETE',
            url: panopto_api_path('session/' + panopto_event.recording.id, {
                key: panopto_event.key,
                loginid: (panopto_event.contact.hasOwnProperty('loginid') &&
                          panopto_event.contact.loginid) ?
                    panopto_event.contact.loginid : '',
                name: panopto_event.recording.name,
                eid: panopto_event.recording.external_id,
                rid: panopto_event.recording.recorder_id,
                feid: panopto_event.recording.folder.external_id,
                rstart: panopto_event.event.start,
                rend: panopto_event.event.end
            })
        }).fail(function (xhr) {
            failure_modal('Cannot Delete Recording',
                          'Please try again later',
                          xhr);
        }).done(function (msg) {
            if (msg.hasOwnProperty('deleted_recording_id') && msg.deleted_recording_id === panopto_event.recording.id) {
                panopto_event.recording.is_broadcast = false;
                panopto_event.recording.is_public = false;
                panopto_event.recording.id = null;
                panopto_event.recording.start = panopto_event.event.start;
                panopto_event.recording.end = panopto_event.event.end;
                if (panopto_event.recording.hasOwnProperty('relocated_recorder_id') &&
                        panopto_event.recording.relocated_recorder_id) {
                    panopto_event.recording.recorder_id = panopto_event.recording.relocated_recorder_id;
                }
            }
        }).always(function () {
            button.trigger('scheduler.remove_schedule_finish', [panopto_event]);
        });
    }

    function panopto_set_recording_time(changes) {
        var start = moment.unix(changes.schedule.start).toISOString(),
            end = moment.unix(changes.schedule.end).toISOString();

        button_loading(changes.schedule.input);
        $.ajax({
            type: 'PUT',
            url: panopto_api_path('session/' +
                changes.panopto_event.recording.id + '/recordingtime'),
            processData: false,
            contentType: 'application/json',
            data: '{' +
                '"start": "' + start + '", ' +
                '"end": "' + end + '"' + '}'
        }).fail(function (xhr) {
            failure_modal('Cannot Modify Recording Time',
                          'Please try again later.',
                          xhr);
        }).done(function () {
            changes.panopto_event.recording.end = end;
            if (start !== end) {
                changes.panopto_event.recording.start = start;
            }
        }).always(function () {
            button_stop_loading(changes.schedule.input);
            update_schedule_buttons(changes.panopto_event);
        });
    }

    function stop_panopto_recording(panopto_event, button) {
        var now;

        if (panopto_is_recording(panopto_event)) {
            now = _now().unix();

            panopto_set_recording_time({
                panopto_event: panopto_event,
                schedule: {
                    start: now,
                    end: now,
                    input: button.closest('.btn-group').find('.slider-box input')
                },
                webcast: null,
                is_public: null
            });
        }
    }

    function panopto_course_schedule_change(event_node) {
        var pe = panopto_event(event_node),
            button_group = event_node.closest('.btn-group');

        return panopto_schedule_change(pe, button_group);
    }

    function panopto_schedule_change(pe, container) {
        var schedule_input = container.find('.slider-box input'),
            webcast_checked = container.find('[name^=webcast_]:checked').val() === '1',
            public_checked = container.find('[name^=public_]:checked').val() === '1',
            schedule_change = null,
            webcast_change = null,
            public_change = null,
            vals,
            now,
            start,
            end;

        if (!pe) {
            return null;
        }

        if ((pe.recording.id && webcast_checked !== pe.recording.is_broadcast) ||
                (!pe.recording.id && webcast_checked)) {
            webcast_change = {
                value: webcast_checked,
            };
        }

        // REMOVE WHEN FEATURE REQUESTED BY SERVICE MANAGER
        //if ((pe.recording.id && public_checked !== pe.recording.is_public)
        //        || (!pe.recording.id && public_checked)) {
        //    public_change = {
        //        value: public_checked,
        //    };
        //}

        start = moment(pe.recording.start).unix();
        end = moment(pe.recording.end).unix();
        if (pe.hasOwnProperty('slider')) {
            vals = pe.slider.slider('getValue');
            if (!(start === vals[0] && end === vals[1])) {
                schedule_change = {
                    start: vals[0],
                    end: vals[1],
                    input: schedule_input
                };
            }
        } else {
            now = _now().unix();
            if (now > start && now < end) {
                schedule_change = {
                    start: now,
                    end: end,
                    input: schedule_input
                };
            }
        }

        return (schedule_change || webcast_change || public_change) ? {
            panopto_event: pe,
            schedule: schedule_change,
            webcast: webcast_change,
            is_public: public_change
        } : null;
    }

    function panopto_set_schedule(e, changes) {
        var pe = panopto_event($(e.target)),
            start,
            now;

        if (!changes) {
            changes = panopto_course_schedule_change($(e.target));
        }

        if (changes && changes.schedule) {
            now = _now();
            start = moment.unix(changes.schedule.start);

            if (start.isBefore(now)) {
                start = now;
            }

            pe.recording.start = start.toISOString();
            pe.recording.end = moment.unix(changes.schedule.end).toISOString();
        }

        if (changes && changes.is_public) {
            pe.recording.is_public = changes.is_public.value;
        }

        if (changes && changes.webcast) {
            pe.recording.is_broadcast = changes.webcast.value;
        }

        schedule_panopto_course_recording(pe);
    }

    function confirm_recording_stop(pe, button) {
        var tpl = Handlebars.compile($('#confirm-record-stop-tmpl').html()),
            modal;

        $('body').append(tpl());
        modal = $('.stop-recording-modal');
        modal.modal();
        modal.find('.modal-footer .stop-recording').on('click', function () {
            stop_panopto_recording(pe, button);
        });
        modal.on('hidden.bs.modal', function (e) {
            $(e.target).remove();
        });
    }

    function confirm_unschedule_event(pe, button) {
        var tpl = Handlebars.compile($('#confirm-unschedule-event-tmpl').html()),
            modal;

        $('body').append(tpl(event_context(pe)));
        modal = $('.unschedule-event-modal');
        modal.modal();
        modal.find('.modal-footer .actually-unschedule-event').on('click', function () {
            remove_scheduled_panopto_recording(pe, button);
        });
        modal.on('hidden.bs.modal', function (e) {
            enable_event_scheduler();
        });
    }

    function panopto_clear_scheduled_recording() {
        /*jshint validthis: true */
        var button = $(this),
            pe = panopto_event(button);

        if (panopto_is_recording(pe)) {
            confirm_recording_stop(pe, button);
        } else {
            remove_scheduled_panopto_recording(pe, button);
        }
    }

    function panopto_schedule_all() {
        /*jshint validthis: true */
        var button = $(this),
            btngrp = button.closest('.btn-group'),
            webcast = btngrp.find('[name^=webcast_][value="1"]').is(':checked'),
            is_public = btngrp.find('[name^=public_][value="1"]').is(':checked'),
            panopto_events = [],
            vals = null,
            start,
            start_delta,
            duration,
            i,
            schedule_all_serially = function (events) {
                var $btngrp,
                    $button;

                if (events.length) {
                    $btngrp = $('[data-schedule-key="' + events[0].key + '"]');
                    $button = $btngrp.find('> button:first-child');
                    $btngrp.one('scheduler.set_schedule_finish', function () {
                        button_stop_loading($button);
                        update_schedule_buttons(events[0]);
                        if (events.length > 1) {
                            schedule_all_serially(events.slice(1));
                        }
                    });

                    schedule_panopto_recording(events[0]);
                }
            };

        if (window.scheduler.hasOwnProperty('global_slider') && window.scheduler.global_slider) {
            vals = window.scheduler.global_slider.slider('getValue');
            start = moment.unix(vals[0]);
            start_delta = start.diff(window.scheduler.global_slider_now, 'seconds');
            duration = moment.unix(vals[1]).diff(start, 'seconds');
        }

        $('.list-group .btn-group.unscheduled > button:first-child').not(':disabled').each(function () {
            var pe = panopto_event($(this)),
                $btngrp = $('[data-schedule-key="' + pe.key + '"]'),
                $button = $btngrp.find('> button:first-child');

            button_loading($button);

            pe.recording.is_broadcast = webcast;
            pe.recording.is_public = is_public;

            if (vals) {
                start = moment(pe.event.start).add(start_delta, 'seconds');
                pe.recording.start = start.toISOString();
                pe.recording.end = start.add(duration, 'seconds').toISOString();
            }

            panopto_events.push(pe);
        });

        schedule_all_serially(panopto_events);
        update_schedule_buttons();
    }

    function panopto_toggle_webcast(e) {
        var target_node = $(e.currentTarget),
            changes = panopto_course_schedule_change(target_node);

        if (changes && changes.panopto_event.recording.id && changes.webcast) {
            button_loading(target_node);

            $.ajax({
                type: 'PUT',
                url: panopto_api_path('session/' +
                    changes.panopto_event.recording.id + '/broadcast'),
                processData: false,
                contentType: 'application/json',
                data: '{ "is_broadcast": ' + (changes.webcast.value ? 'true' : 'false') +  '}'
            }).fail(function (xhr) {
                failure_modal('Cannot Set Broadcast Permissions',
                              'Please try again later.',
                              xhr);
            }).done(function () {
                changes.panopto_event.recording.is_broadcast = changes.webcast.value;
            }).always(function () {
                button_stop_loading(target_node);
                update_schedule_buttons(changes.panopto_event);
            });
        } else {
            panopto_set_schedule(e, changes);
        }
    }

    function panopto_toggle_public(e) {
        var target_node = $(e.currentTarget),
            changes = panopto_course_schedule_change(target_node);

        if (changes && changes.panopto_event.recording.id && changes.is_public) {
            button_loading(target_node);

            $.ajax({
                type: 'PUT',
                url: panopto_api_path('session/' +
                    changes.panopto_event.recording.id + '/public'),
                processData: false,
                contentType: 'application/json',
                data: '{ "is_public": ' + (changes.is_public.value ? 'true' : 'false') +  '}'
            }).fail(function (xhr) {
                failure_modal('Cannot Set Public Permissions',
                              'Please try again later.',
                              xhr);
            }).done(function () {
                changes.panopto_event.recording.is_public = changes.is_public.value;
            }).always(function () {
                button_stop_loading(target_node);
                update_schedule_buttons(changes.panopto_event);
            });
        } else {
            panopto_set_schedule(e, changes);
        }
    }

    function panopto_modify_recording_time(e) {
        var changes = panopto_course_schedule_change($(e.currentTarget));

        if (changes) {
            if (changes.panopto_event.recording.id && changes.schedule) {
                panopto_set_recording_time(changes);
            } else {
                panopto_set_schedule(e, changes);
            }
        }
    }

    function init_schedule_dropdown() {
        /*jshint validthis: true */
        var pe = panopto_event($(this)),
            button_group = $(this).closest('.btn-group'),
            $box = $('.slider-box', button_group),
            slider = $box.find('input'),
            start_span = $box.find('.start-time'),
            end_span = $box.find('.slider-box'),
            range,
            checked,
            event_start_date,
            event_end_date,
            slider_instance,
            slider_value,
            recording_start,
            recording_end,
            now = _now();

        if (pe) {
            range = init_slider_range(pe.event.start, pe.event.end,
                                      pe.recording.start, pe.recording.end);
            event_start_date = range.event.start_date;
            event_end_date = range.event.end_date;
            slider_value = range.slider_value;
        } else if (window.scheduler.events) {
            $.each(window.scheduler.events, function () {
                var this_event_start = moment(this.event.start);

                if (this_event_start.isBefore(now)) {
                    return true;
                }

                if (!event_start_date) {
                    event_start_date = this_event_start;
                } else if (event_start_date.format('hh:mm a') !== moment(this.event.start).format('hh:mm a')) {
                    event_start_date = null;
                    slider_value = null;
                    return false;
                }

                if (!event_end_date) {
                    event_end_date = moment(this.event.end);
                } else if (event_end_date.format('hh:mm a') !== moment(this.event.end).format('hh:mm a')) {
                    event_end_date = null;
                    slider_value = null;
                    return false;
                }
            });

            if (event_start_date && event_end_date) {
                recording_start = moment(moment(event_start_date));
                recording_end = moment(event_end_date);
                slider_value = [
                    recording_start.unix(),
                    recording_end.unix()
                ];
            }
        } else {
            return;
        }

        checked = (pe && pe.recording.id && pe.recording.is_broadcast) ? '1' : '0';
        $('input[name^=webcast_][value="' + checked + '"]', button_group).prop('checked', true);

        checked = (pe && pe.recording.id && pe.recording.is_public) ? '1' : '0';
        $('input[name^=public_][value="' + checked + '"]', button_group).prop('checked', true);

        if (slider_value) {
            $('.recording-duration-slider', button_group).removeClass('hidden');
            if (slider.hasClass('duration-slider-enabled') && pe && pe.slider) {
                start_span.html(moment(slider_value[0]).format('h:mm a'));
                end_span.html(moment(slider_value[1]).format('h:mm a'));
                pe.slider.slider('setValue', slider_value);
            } else {
                slider.addClass('duration-slider-enabled');
                slider_instance = init_slider_box($box,
                                                  pe ? pe.event.start : event_start_date.toISOString(),
                                                  pe ? pe.event.end : event_end_date.toISOString(),
                                                  pe ? pe.recording.start : recording_start.toISOString(),
                                                  pe ? pe.recording.end : recording_end.toISOString());

                slider_instance.on('slideStop', function (e) {
                    panopto_modify_recording_time(e);
                });

                if (pe) {
                    pe.slider = slider_instance;
                    window.scheduler.global_slider = null;
                } else {
                    window.scheduler.global_slider = slider_instance;
                    window.scheduler.global_slider_now = recording_start;
                }
            }
        } else {
            $('.recording-duration-slider', button_group).addClass('hidden');
        }
    }

    function position_schedule_dropdown() {
        /*jshint validthis: true */
        var button_group = $(this).closest('.btn-group'),
            menu = $('.dropdown-container', button_group),
            bottom = menu.offset().top +
                menu.height() +
                $('.dropdown-menu', menu).height() +
                12; // slider fudge

        if (bottom - $(document).scrollTop() > $(window).height()) {
            menu.removeClass('dropdown');
            menu.addClass('dropup');
        } else {
            menu.removeClass('dropup');
            menu.addClass('dropdown');
        }
    }

    function schedule_options_closing(e) {
        if ($('.modal-dialog').length) {
            e.preventDefault();
        }
    }

    function event_scheduler(e) {
        /*jshint validthis: true */
        var pe = panopto_event($(this)),
            context = event_context(pe),
            tpl = Handlebars.compile($('#reservation-panel-tmpl').html()),
            slider_instance,
            checked;

        context.location = $('select#room-select option:selected').text();
        context.search_date = moment($('input#calendar.input-date').val()).format('MMMM D, YYYY');
        $('.result-display-container').html(tpl(context));

        slider_instance = init_slider_box($('.slider-box'),
                                          pe.event.start, pe.event.end,
                                          pe.recording.start, pe.recording.end);

        pe.slider = slider_instance;
/*
        $('.reservation-settings .foldername .folder-picker .search input').data(
            'finish', search_panopto_folders);

        $('.reservation-settings .foldername .form-group > input').data(
            'finish', validate_new_folder);

        $('.reservation-settings .creators .form-group > input').data(
            'finish', panopto_folder_string_to_creators);
*/

        slider_instance.on('slideStop', function (e) {
            var v = slider_instance.slider('getValue'),
                start = parseInt(v[0], 10),
                end = parseInt(v[1], 10);

            window.scheduler.slider_val = v;
            $('button .start-time').html(moment.unix(start).format('h:mma'));
            $('button .end-time').html(moment.unix(end).format('h:mma'));
        });

        checked = (pe && pe.recording.id && pe.recording.is_public) ? '1' : '0';
        $('input[name^=public_][value="' + checked + '"]').prop('checked', true);

        checked = (pe && pe.recording.id && pe.recording.is_broadcast) ? '1' : '0';
        $('input[name^=webcast_][value="' + checked + '"]').prop('checked', true);

        validate_event_folder(pe.recording.folder.name, null);
    }

    function event_scheduler_cancel(e) {
        find_event_from_search(window.location.search);
    }

    function event_scheduler_finish(e) {
        var $node = $('.reservation-settings[data-schedule-key]'),
            pe = window.scheduler.events[$node.attr('data-schedule-key')],
            modal,
            text = 'Issues with the created folder:<br><ul>';

        if (pe.hasOwnProperty('create_messages')) {
            $.each(pe.create_messages, function () {
                text += '<li>' + this + '</li>';
            });

            text += '</ul>';

            modal = failure_modal(
                "Recording scheduled, but issues were reported", text);

            modal.on('hidden.bs.modal', function (e) {
                find_event_from_search(window.location.search);
            });
        } else {
            find_event_from_search(window.location.search);
        }
    }
/*
    function search_panopto_folders(substring) {
        var term = substring.trim();

        if (term.length > 3) {
            search_in_progress('.folder-picker .result');
            do_panopto_folder_search(term, null, search_panopto_folders_complete);
        }
    }
*/
/*
    function validate_new_folder(substring) {
        var folder = substring.trim();

        if (folder.length < 1 || folder === $('.foldername .field a').text()) {
            return;
        }

        validate_panopto_folder(folder);
    }
*/
    function validate_event_folder(folder, parent_folder_id) {
        /*jshint validthis: true */
//        var creators;

//        $('.foldername .field a').text(folder);
//        panopto_folder_string_to_creators();
//        close_panopto_event_field_editors();

//        $('.foldername input.original-folder').val('');
//        $('.foldername input.folder-id').val('');
//        $('a.visit-folder').addClass('hidden');

        disable_event_scheduler();
        $('button.schedule-event').addClass('loading');

        // fix up creators and links
//        $('.folder-exists').addClass('hidden');
//        $('a.visit-folder').attr('disabled', 'disabled');

        do_panopto_folder_search(folder, parent_folder_id, function (data) {
            display_event_folder(folder, parent_folder_id, data);
        });
    }

    function display_event_folder(folder, parent_folder_id, data) {
        var $folder_div = $(".reservation-settings .event-folder"),
            tpl = Handlebars.compile($('#event-folder-tmpl').html()),
            context = {
                path: [],
                folders: [{
                    name: folder,
                    id: null,
                    parent_folder_id: parent_folder_id
                }],
                folder: {
                    name: folder,
                    id: null,
                    parent_folder_id: parent_folder_id
                },
                creator_netids: []
            },
            found_folder;

        enable_event_scheduler();
        $('button.schedule-event').removeClass('loading');
        if ($.isArray(data)) {
            if (data.length == 0) {
                $folder_div.html(tpl(context));
                // not found
                disable_event_schedule_button();
            } else if (data.length > 1) {
                // too many found, display search result?
                $folder_div.html(tpl(context));
                disable_event_schedule_button();
            } else {
                found_folder = panopto_folders_from_search(data);
                if (!found_folder || found_folder.folders.length > 1) {
                    // too many found, display search result?
                    $folder_div.html(tpl(context));
                    disable_event_schedule_button();
                }

                context.folders = found_folder.folders;
                context.folder = found_folder.folders[0];
                context.path = found_folder.path;

                $folder_div.html(tpl(context));
                enable_event_schedule_button();
            }
        }
    }

    function panopto_folders_from_search(data, folder) {
        if (!folder) {
            folder = {
                path: [],
                folders: []
            };
        }

        for (var i = 0; i < data.length; i += 1) {
            var f = data[i];

            if (f.hasOwnProperty('name')) {
                if (f.child_folders.length) {
                    folder.path.push(f);
                    return panopto_folders_from_search(f.child_folders, folder);
                } else {
                    folder.folders.push(f);
                }
            }
        }

        return folder;
    }

    function do_panopto_folder_search(folder, parent_folder_id, finished) {
        $.ajax({
            type: 'GET',
            url: panopto_api_path('folder/', {
                search: folder,
                parent_folder_id: (parent_folder_id) ? parent_folder_id : ''
            })
        })
            .fail(function (jqXHR, textStatus) {
                alert('Folder search failed: ' + (jqXHR.responseJSON ? jqXHR.responseJSON.error : jqXHR.responseText));
                display_event_folder(folder, parent_folder_id, []);
            })
            .done(finished);
    }

    function do_panopto_folder_create(folder_name, parent_folder_id, finished) {
        $.ajax({
            type: 'POST',
            url: panopto_api_path('folder/'),
            contentType: 'application/json',
            data: JSON.stringify({
                'folder_name': folder_name,
                'parent_folder_id': (parent_folder_id) ? parent_folder_id : ''
            })//,
            //waitIndicatator: event_folder_search_in_progress,
            //complete: event_folder_search_complete
        })
            .fail(function (jqXHR, textStatus) {
                alert('Folder create failed: ' + (jqXHR.responseJSON ? jqXHR.responseJSON.error : jqXHR.responseText));
            })
            .done(finished);
    }

    function open_panopto_event_folder_editor() {
        var $form = $('.event-folder .form-group'),
            folder = $('.folder-name .folder', $form).text(),
            $editor_folders;

        disable_event_schedule_button();
        $('.folder-editor .original-folder', $form).val(folder);
        $('.folder-editor', $form).removeClass('hidden');
        $('.folder-name', $form).addClass('hidden');
        $('.folder-editor .folder', $form).val(folder).focus();

        // copy folder path and make it editable
        $editor_folders = $('.folder-editor .folder-path', $form);
        $editor_folders.empty();
        $('.folder-name .folder-path .path-element', $form).each(function (i) {
            var $clone = $(this).clone();

            $clone.find('span').replaceWith(
                $('<a>').text($(this).text()).addClass("directory").attr('href', 'javascript:void(0);'));
            $clone.addClass('collapsable');
            if (i > 0) {
                $clone.addClass('hidden');
            }

            $editor_folders.append($clone);
        });
    }

    function cancel_panopto_event_folder_editor() {
        var $form = $('.event-folder .form-group');

        $('.folder-name .folder-path .path-element:not(:first-child)', $form).addClass('hidden');
        $('.folder-name', $form).removeClass('hidden');
        $('.folder-editor', $form).addClass('hidden');
    }

    function panopto_event_folder_search(e) {
        var $form = $('.event-folder .form-group'),
            $result = $('.folder-search-result', $form),
            $input = $('.folder-editor input.folder', $form),
            folder = $input.val().trim(),
            parent_folder_id = $input.attr('data-parent-folder-id');

        if (folder.length < 5) {
            return;
        }

        $result.empty().addClass('loading').removeClass('hidden no-result');
        do_panopto_folder_search(folder, parent_folder_id, function (data) {
            var tpl = Handlebars.compile($('#event-folder-search-result-tmpl').html());

            $result.removeClass('loading');

            if (data.length == 0) {
                $result.addClass('no-result');
                return;
            }

            for (var i = 0; i < data.length; i += 1) {
                var found_folder = panopto_folders_from_search([data[i]]);
                $result.append(tpl(found_folder));
            }
        });
    }
    function panopto_event_folder_clear(e) {
        var $form = $('.event-folder .form-group'),
            $result = $('.folder-search-result', $form),
            $input = $('.folder-editor input.folder', $form),
            $folder_path = $('.folder-editor .folder-path', $form);

        $result.empty().addClass('hidden');
        update_event_folder_editor_cues();
        $input.val('')
            .attr('placeholder', 'Search for or create folder name (at least 8 chars)')
            .attr('data-parent-folder-id', '');
        $folder_path.empty();
    }

    function select_panopto_event_folder_from_search(e) {
        /*jshint validthis: true */
        var $a = $(this),
            folder = $a.text(),
            $element = $a.parent(),
            $input = $a.closest('.folder-editor').find('input.folder'),
            parent_folder_id = $a.closest('.folders').attr('data-parent-folder-id'),
            $path = $([]);

        $a.closest('.folder-name').find('.folder-path .path-element').each(function () {
            var $path_element = $(this);

            $path.push($path_element.clone());
            if ($path_element.attr('data-folder-id') == parent_folder_id) {
                return false;
            }
        });

        e.preventDefault();
        e.stopPropagation();

        $input.val(folder)
            .attr('data-parent-folder-id', parent_folder_id);
        copy_panopto_event_search_folder_path_to_editor($path);
        close_panopto_folder_search_result();
        update_event_folder_editor_cues();
    }

    function select_panopto_event_directory_from_search(e) {
        /*jshint validthis: true */
        var $a = $(this),
            $element = $a.parent(),
            $path = $($element.prevAll('div.path-element').get().reverse()).clone(),
            $input = $element.closest('.folder-editor').find('input.folder');

        e.preventDefault();
        e.stopPropagation();

        $input.val('').attr('data-parent-folder-id', $element.attr('data-folder-id'));
        $path.push($element.clone());
        copy_panopto_event_search_folder_path_to_editor($path);
        close_panopto_folder_search_result();
        update_event_folder_editor_cues();
    }

    function copy_panopto_event_search_folder_path_to_editor($path) {
        var $folder_path = $('.event-folder .folder-details .folder-editor .folder-path');

        $folder_path.empty();
        $path.each(function (i) {
            var $this = $(this);

            if (i > 0) {
                $this.removeClass('hidden');
                $this.addClass('collapsable');
            }

            $folder_path.append($this);
        });
    }

    function close_panopto_folder_search_result() {
        var $editor = $('.event-folder .form-group .folder-editor');

        $('.folder-search-result', $editor).empty().addClass('hidden');
        $('input.folder', $editor).focus();
    }

    function collapse_expand_event_folder_path_element(e) {
        /*jshint validthis: true */
        var $i = $(this),
            $element = $i.parent(),
            $input = $i.closest('.folder-editor').find('input.folder'),
            parent_folder_id = $input.attr('data-parent-folder-id'),
            in_search_result = $element.closest('.folder-search-result').length > 0,
            in_editor = $element.closest('.folder-editor').length > 0,
            is_first = $element.prev('.path-element').length > 0,
            $prev = is_first ? $element: $element.prev('.path-element'),
            $next = $element.next('.path-element'),
            expand = $next.hasClass('hidden');

        if ($i.hasClass('fa-folder')) {
            $element.nextAll('.path-element').each(function () {
                var $element = $(this);

                if (expand) {
                    $element.find('i').addClass('fa-caret-down').removeClass('fa-caret-right');
                    $element.removeClass('hidden');

                    if (in_search_result) {
                        $element.closest('.folder-name').find('.folders').removeClass('hidden');
                    }

                    if (in_editor && parent_folder_id) {
                        if ($element.attr('data-folder-id') == parent_folder_id) {
                            return false;
                        }
                    }
                } else {
                    $element.addClass('hidden');
                    $element.find('i').removeClass('fa-caret-down').addClass('fa-caret-right');

                    if (in_search_result) {
                        $element.closest('.folder-name').find('.folders').addClass('hidden');
                    }
                }
            });

            return;
        }

        if ($next.length == 0 || expand) {
            $i.removeClass('fa-caret-right').addClass('fa-caret-down');
            $next.removeClass('hidden');
            $input.attr('data-parent-folder-id', $next.attr('data-folder-id'));
        } else {
            $i.removeClass('fa-caret-down').addClass('fa-caret-right');
            $element.nextAll('.path-element')
                .addClass('hidden')
                .find('i')
                .removeClass('fa-caret-down')
                .addClass('fa-caret-right');
            $input.attr('data-parent-folder-id', $prev.attr('data-folder-id'));
        }

        update_event_folder_editor_cues();
    }

    function update_event_folder_editor_cues() {
        var $editor = $('.reservation-settings .folder-editor'),
            $input = $editor.find('input.folder'),
            parent_folder_id = $input.attr('data-parent-folder-id'),
            $create_link = $editor.find('a.event-folder-create'),
            $search_link = $editor.find('span.folder-search'),
            folder_name = parent_folder_id ? $('.path-element[data-folder-id="' + parent_folder_id + '"]').text() : "top level directory";

        $input
            .attr('placeholder', 'Create or Search in "' + folder_name.trim() + '"')
            .attr('data-parent-folder-id', parent_folder_id);
        $search_link.attr('title', 'Search for folder in ' + folder_name);
        $create_link.text('Create folder in ' + folder_name);
    }

    function panopto_event_folder_editor_input(e) {
        /*jshint validthis: true */
        var $input = $(this),
            $form = $('.event-folder .form-group'),
            $save = $('.event-folder-create', $form),
            name = $input.val().trim(),
            original = $('.reservation-settings .original-folder', $form).val();

        e.preventDefault();
        e.stopPropagation();

        if (name == original) {
            $save.addClass('disabled');
        } else {
            $save.removeClass('disabled');
        }
    }

    function close_panopto_event_field_editors() {
        var $hidden = $('.field-editor .field.hidden'),
            $fields;

        if ($hidden.length) {
            $fields = $hidden.parent();
            $fields.trigger('scheduler.field_edit_closing');
            $fields.find('.form-group').addClass('hidden').removeClass('has-error');
            $fields.find('.field').removeClass('hidden');
        }
    }

    function init_slider_range(event_start, event_end, rec_start, rec_end) {
        var event_start_date,
            event_end_date,
            recording_start,
            recording_end,
            slider_value = null,
            now = _now();

        event_start_date = moment(event_start);
        event_end_date = moment(event_end);
        recording_start = moment(rec_start);
        recording_end = moment(rec_end);
        if (recording_start.isBefore(now)) {
            recording_start = now;
        }

        if (recording_start && recording_end) {
            slider_value = [
                recording_start.unix(),
                recording_end.unix()
            ];
        }

        var orig_event_start = moment(event_start),
            buffered_event_start = moment(orig_event_start).subtract(
                window.scheduler.event_start_time_buffer, 'seconds');

        return {
            event: {
                start_date: buffered_event_start,
                end_date: moment(event_end)
            },
            slider_value: slider_value
        };
    }

    function init_slider_box($box, event_start, event_end, rec_start, rec_end) {
        var slider = $box.find('input'),
            start_span = $box.find('.start-time'),
            end_span = $box.find('.end-time'),
            range = init_slider_range(event_start, event_end, rec_start, rec_end),
            slider_instance,
            now = _now();

        start_span.html(range.event.start_date.format('h:mm a'));
        end_span.html(range.event.end_date.format('h:mm a'));

        if (range.slider_value) {
            slider.addClass('duration-slider-enabled');
            slider_instance = slider.slider({
                min: range.event.start_date.unix(),
                max: range.event.end_date.unix(),
                value: range.slider_value,
                step: 60,
                tooltip: 'hide',
                formatter: function (v) {
                    var start = parseInt(v[0], 10),
                        end = parseInt(v[1], 10);

                    if ($.isArray(v) && v.length === 2) {
                        start_span.html(moment.unix(start).format('h:mm a'));
                        end_span.html(moment.unix(end).format('h:mm a'));
                    }

                    return ((end - start) / 60) + ' minutes';
                }
            });

            slider_instance.on('slideStart', function () {
                window.scheduler.slider_val = slider_instance.slider('getValue');
                window.scheduler.slider_left = null;
            });

            slider_instance.on('slide', function () {
                var min_slide = 60,  // one minute
                    val = slider_instance.slider('getValue'),
                    slid;

                if (window.scheduler.slider_left === null) {
                    window.scheduler.slider_left = (window.scheduler.slider_val[0] !== val[0]);
                }

                if (window.scheduler.slider_left && (window.scheduler.slider_val[1] !== val[1])) {
                    val[1] = window.scheduler.slider_val[1];
                    slider_instance.slider('setValue', val);
                } else if (!window.scheduler.slider_left && (window.scheduler.slider_val[0] !== val[0])) {
                    val[0] = window.scheduler.slider_val[0];
                    slider_instance.slider('setValue', val);
                }

                if ((val[1] - val[0]) < min_slide) {
                    if (window.scheduler.slider_left) {
                        val[0] = val[1] - min_slide;
                    } else {
                        val[1] = val[0] + min_slide;
                    }

                    slider_instance.slider('setValue', val);
                }

                if (now.isAfter(range.event.start_date) && now.isBefore(range.event.end_date)) {
                    slid = _now();

                    if (val[0] < slid.unix()) {
                        val[0] = slid.unix();
                        slider_instance.slider('setValue', val);
                    }
                }
            });
        }

        return slider_instance;
    }

    function parse_sis_id(sis_id) {
        var parts = sis_id.match(/^(\d{4})-(winter|spring|summer|autumn)-([\w& ]+)-(\d{3})-([A-Z][A-Z0-9]?)$/);

        if (parts) {
            return {
                term: [parts[1], parts[2]].join('-').toLowerCase(),
                curriculum: parts[3],
                number: parts[4],
                section: parts[5],
                sws_label: [parts[1], parts[2], parts[3], parts[4]].join(',') + '/' + parts[5],
                canvas_id: sis_id
            };
        }

        return null;
    }

    function panopto_recorder_details(data) {
        var tpl = Handlebars.compile($('#recorder-selection-tmpl').html()),
            context = {
                server: window.scheduler.panopto_server,
                name: data[0].name,
                id: data[0].id,
                state: data[0].state,
                settings_url: data[0].settings_url,
                external_id: data[0].external_id,
                space: data[0].space,
                scheduled_recordings: data[0].scheduled_recordings
            };

        $('.result-display-container').html(tpl(context));

        do_scheduled_recording_search(data[0].scheduled_recordings);
    }

    function panopto_recorder_search() {
        var recorder = $('#panopto-recorders #room-select').find('option:selected').val(),
            ids;

        if (recorder.length) {
            ids = recorder.split('|');
        } else {
            return;
        }

        $.ajax({
            type: 'GET',
            url: panopto_api_path('recorder/' + ids[1]),
            waitIndicatator: recorder_select_in_progress,
            complete: room_search_complete
        })
            .fail(recorder_select_failure)
            .done(panopto_recorder_details);
    }

    function panopto_space_search(modal, query) {
        var select = modal.find('#new-room-search-result'),
            spinner = modal.find('#new-room-search + span'),
            assign = modal.find('.modal-footer .assign-room');

        spinner.show();

        $.ajax({
            type: 'GET',
            url: panopto_api_path('space/', { contains: query }),
            complete: function () {
                spinner.hide();
            }
        })
            .fail(function (xhr) {
                console.log("FAIL " + xhr.responseText);
            })
            .done(function (data) {
                select.find('option').remove();
                if (data && data.length) {
                    assign.removeAttr('disabled');
                } else {
                    assign.attr('disabled', 'disabled');
                }


                $.each(data, function () {
                    select.append($('<option></option>')
                                  .text(this.name)
                                  .attr('value', this.space_id)
                                  .attr('title', 'space ' + this.name));
                });
            });
    }

    function panopto_update_recorder(request_data) {
        $.ajax({
            type: 'PUT',
            url: panopto_api_path('recorder/' +
                $('.recorder-selection #recorder-id').val()),
            processData: false,
            contentType: 'application/json',
            data: JSON.stringify(request_data)
        }).fail(function (xhr) {
            failure_modal('Cannot Schedule Recording',
                          'Please try again later.',
                          xhr);
        }).done(function () {
            panopto_recorder_search();
        });
    }

    function panopto_change_space(e) {
        var tpl = Handlebars.compile($('#assign-space-tmpl').html()),
            modal;

        e.preventDefault();

        $('body').append(tpl());
        modal = $('.assign-space-modal');
        modal.modal();
        modal.find('.modal-footer .assign-room').on('click', function () {
            var selected = modal.find('#new-room-search-result option:selected');

            if (selected && selected.length) {
                panopto_update_recorder({
                    name: $('.recorder-selection #recorder-name').val().trim(),
                    external_id: selected.val()
                });
            }
        });
        modal.on('hidden.bs.modal', function (e) {
            $(e.target).remove();
        });
        modal.on('shown.bs.modal', function () {
            $('#new-room-search').on('keypress', function (e) {
                var c = String.fromCharCode(e.keyCode),
                    val = $(e.target).val().trim();

                if ((c.match(/\w/) || e.keyCode === 8 || e.keyCode === 46) && val.length >= 1) {
                    panopto_space_search(modal, val + c);
                } else if (e.which === 13) {
                    e.preventDefault();
                }
            })
                .focus();
        });
    }

    function panopto_remove_space() {
        if ($('.recorder-selection #space-id').val().length) {
            if (confirm('Sure you want to remove the room assignment?')) {
                $('.remove-room').hide().next('span').show();
                panopto_update_recorder({
                    name: $('.recorder-selection #recorder-name').val().trim(),
                    external_id: ''
                });
            }
        } else {
            $('.remove-room').blur();
        }
    }

    function _now() {
        return window.scheduler.hasOwnProperty('current_date') ?
            moment(window.scheduler.current_date) : moment();
    }

    function init_course_events() {
        $('body')
            .on('click',
                '.batchswitch .btn-group > button:first-child',
                panopto_schedule_all)
            .on('click',
                '.list-group .btn-group.unscheduled > button:first-child,' +
                '.list-group .btn-group.can-record > button:first-child',
                panopto_set_schedule)
            .on('click',
                '.list-group .btn-group.scheduled > button:first-child,' +
                '.list-group .btn-group.is_recording > button:first-child',
                panopto_clear_scheduled_recording)
            .on('scheduler.remove_schedule_start', '.btn-group button',
                function (e, panopto_event) {
                    button_loading($(this));
                })
            .on('scheduler.remove_schedule_finish', '.btn-group button',
                function (e, panopto_event) {
                    button_stop_loading($(this));
                    update_schedule_buttons(panopto_event);
                })
            .on('show.bs.dropdown',
                '.schedule-button-cluster .btn-group',
                init_schedule_dropdown)
            .on('hide.bs.dropdown',
                '.list-group .btn-group',
                schedule_options_closing)
            .on('mousedown',
                '.list-group .btn-group button.dropdown-toggle',
                position_schedule_dropdown)
            .on('change',
                '.list-group .btn-group input[name^=webcast_]',
                panopto_toggle_webcast)
            .on('change',
                '.list-group .btn-group input[name^=public_]',
                panopto_toggle_public)
            .on('click',
                '.dropdown-menu',
                function (e) { e.stopPropagation(); });
        Handlebars.registerPartial('reservation-list', $('#reservation-list-partial').html());
        Handlebars.registerPartial('schedule-button', $('#schedule-button-partial').html());
    }

    function init_event_events() {
        $('body')
            .on('click', 'a.schedule-recording, a.edit-recording',
                event_scheduler)
            .on('click', '.reservation-settings .cancel',
                event_scheduler_cancel)
            .on('mouseup', function(e) {
                var $editor = $('.event-folder .form-group .folder-editor');

                if ($editor.length && !$editor.hasClass('hidden') && !$(e.target).closest('.folder-search-result').length) {
                    close_panopto_folder_search_result();
                }
            })
            .on('click', '.reservation-settings .event-folder-edit',
                open_panopto_event_folder_editor)
            .on('click', '.reservation-settings .folder-name .event-folder-create', function (e) {
                var folder_name = $('.reservation-settings .original-folder').val(),
                    parent_folder_id = $('.reservation-settings .original-folder-id').val();

                do_panopto_folder_create(folder_name, parent_folder_id, function () {
                    alert('crated');
                });
            })
            .on('click', '.reservation-settings .folder-editor .event-folder-create', function (e) {
                var $form = $('.event-folder .form-group'),
                    $input = $('.folder-editor input.folder', $form),
                    folder_name = $input.val().trim(),
                    parent_folder_id = $input.attr('data-parent-folder-id');

                do_panopto_folder_create(folder_name, parent_folder_id, function () {
                    alert('created');
                });
            })
            .on('click', '.reservation-settings .event-folder-cancel',
                cancel_panopto_event_folder_editor)
            .on('keyup', '.reservation-settings .folder-editor input.folder',
                panopto_event_folder_editor_input)
            .on('click', '.reservation-settings .folder-editor input.folder ~ .folder-search',
                panopto_event_folder_search)
            .on('click', '.reservation-settings .folder-editor input.folder ~ .folder-clear',
                panopto_event_folder_clear)
            .on('click', '.reservation-settings .folder-editor .folder-search-result .folder',
                select_panopto_event_folder_from_search)
            .on('click', '.reservation-settings .folder-editor > .folder-search-result .directory',
                select_panopto_event_directory_from_search)
            .on('click', '.reservation-settings .folder-editor > .folder-path .directory', function (e) {
                var $path_element = $(this).parent();

                $path_element.nextAll().addClass('hidden');
                update_event_folder_editor_cues($path_element);
            })
            .on('scheduler.field_edit_clearing', '.foldername',
                function () {
                    $('.reservation-settings .foldername .folder-picker .result').html('');
                })
            .on('click', '.field-editor .form-group', function (e) {
                e.stopPropagation();
            })
            .on('click', '.schedule-event',
                schedule_panopto_event_recording)
            .on('click', '.unschedule-event',
                unschedule_panopto_event_recording)
            .on('scheduler.set_schedule_finish', '[data-schedule-key]',
                event_scheduler_finish)
            .on('scheduler.remove_schedule_start', 'button',
                function (e, panopto_event) {
                    $('.unschedule-event-modal')
                        .find('a, button, input')
                        .attr('disabled', 'disabled');
                })
            .on('scheduler.remove_schedule_finish', 'button',
                function (e, panopto_event) {
                    $('.unschedule-event-modal').modal().hide();
                    find_event_from_search(window.location.search);
                })
            .on('click', '.modify-event',
                modify_panopto_event_recording)
            .on('click', '.folder-name .path-element.collapsable > i, .folder-editor .path-element.collapsable > i',
                collapse_expand_event_folder_path_element);

        Handlebars.registerHelper('indent', function (value) {
	        return value * 8;
        });
    }

    function initialize() {
        $.ajaxSetup({
            crossDomain: false, // obviates need for sameOrigin test
            beforeSend: function (xhr, settings) {
                if (this.hasOwnProperty('waitIndicatator')) {
                    this.waitIndicatator();
                }
                if (window.scheduler.session_id) {
                    xhr.setRequestHeader("X-SessionId", window.scheduler.session_id);
                }
                if (!csrfSafeMethod(settings.type)) {
                    xhr.setRequestHeader("X-CSRFToken", window.scheduler.csrftoken);
                }
            }
        });

        if ($('form.course-search').length) {
            init_term_selector();
            $("form.course-search").submit(do_course_search);
            init_course_events();

            if (window.location.search.length) {
                find_course_from_search(window.location.search);
                $(window).bind('popstate', function (e) {
                    var search = e.originalEvent.path[0].location.search;
                    find_course_from_search(search);
                    });
                }
        } else if ($('#panopto-recorders').length) {
            init_recorder_search();
            $('body')
                .on('change', '#panopto-recorders #room-select', panopto_recorder_search)
                .on('click', '.recorder-selection .change-room', panopto_change_space)
                .on('click', '.recorder-selection .remove-room', panopto_remove_space);
            Handlebars.registerPartial('schedule-button', $('#schedule-button-partial').html());
        } else if ($('form.event-search').length) {
            init_event_search();
            init_date_picker();
            $("form.event-search").submit(do_event_search);
            init_event_events();

            if (window.location.search.length) {
                find_event_from_search(window.location.search);
                $(window).bind('popstate', function (e) {
                    var search = e.originalEvent.path[0].location.search;
                    find_event_from_search(search);
                });
            }

            //history.replaceState({}, '', search_param ? search_param : '/scheduler/');
        } else {
            // if blti loaded
            if (window.scheduler.hasOwnProperty('blti')) {
                find_course(parse_sis_id(window.scheduler.blti.course));
            }

            init_course_events();
        }
    }

    $(document).ready(initialize);

}(jQuery));
