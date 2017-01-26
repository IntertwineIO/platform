
$(document).ready(function() {
    var payload = JSON.parse($('#payload').val());
    var rootKey = payload['root_key'];
    var community = payload[rootKey];
    var problemKey = community['problem'];
    var problem = problemKey ? payload[problemKey]: null;
    var orgKey = community['org'];
    var org = orgKey ? payload[orgKey]: null;
    var geoKey = community['geo'];
    var geo = geoKey ? payload[geoKey]: null;

    var isAddingConnection = {'driver': false, 'impact': false, 'broader': false, 'narrower': false};
    var animateDuration = 1000;

    function scrollTo(direction, axis, scrollDiv) {
        var directionSign = (direction == 'beginning') ? 1 : ((direction == 'end') ? -1 : null);
        if (axis == 'causal') {
            scrollDiv.animate({
                scrollTop: (scrollDiv[0].clientHeight - scrollDiv[0].scrollHeight) * directionSign
            }, animateDuration);
        } else if (axis == 'scoped') {
            scrollDiv.animate({
                scrollLeft: (scrollDiv[0].clientWidth - scrollDiv[0].scrollWidth) * directionSign
            }, animateDuration);
        }
    }

    function deriveAxis(category) {
        if (category == 'driver' || category == 'impact') {
            axis = 'causal';
        } else if (category == 'broader' || category == 'narrower') {
            axis = 'scoped';
        } else {
            console.log('Unknown category: ' + category);
        }
        return axis;
    }

    function renderAddConnectionForm(category) {
        return (
            '<form id="add-' + category + '-connection-form" class="add-connection-form" action="add-' + category + '-connection" method="post">\n' +
                '<input id="' + category + '-problem-name-input" class="adjacent-problem-name-input" type="text" name="' + category + '-problem-name-input" maxlength="60" placeholder="Problem Name"><br>\n' +
                '<a href=# id="submit-add-' + category + '-connection" class="submit-add-adjacent-connection-link"><i class="fa fa-check submit-icon" aria-hidden="true"></i> Add </a>\n' +
                '<a href=# id="cancel-add-' + category + '-connection" class="cancel-add-adjacent-connection-link"><i class="fa fa-times cancel-icon" aria-hidden="true"></i> Cancel </a>\n' +
            '</form>\n');
    }

    function renderAddConnectionFormContainer(category) {
        var begHTML, adjacentProblemNameHTML, adjacentProblemIconHTML, endHTML;
        var renderedConnectionForm;
        var axis = deriveAxis(category);
        var connectionScroll = $('#' + category + '-scroll');

        if (isAddingConnection[category]) {
            scrollTo('beginning', axis, connectionScroll);
            $('#' + category + '-problem-name-input').focus()
            return;
        }
        isAddingConnection[category] = true;

        if (axis == 'causal') {
            begHTML = '<div id="add-' + category + '-connection-component" class="v-problem">\n';
            adjacentProblemNameHTML = (
                '<div class="v-problem-link-container v-align-inner word-break">\n' +
                    renderAddConnectionForm(category) +
                '</div>\n');
            adjacentProblemIconHTML = (
                '<div class="v-align-inner">\n' +
                    '<i class="fa fa-circle problem-icon ' + category + '-icon"></i>\n' +
                '</div>\n');
            endHTML = '</div>\n';
            renderedConnectionForm = (category == 'driver') ?
                begHTML + adjacentProblemNameHTML + adjacentProblemIconHTML + endHTML :
                begHTML + adjacentProblemIconHTML + adjacentProblemNameHTML + endHTML
        } else if (axis == 'scoped') {
            begHTML = '<div id="add-' + category + '-connection-component" class="h-problem add-scoped-connection-container ' + category + '-problem">\n';
            adjacentProblemNameHTML = (
                '<div class="h-problem-link-container word-break">\n' +
                    renderAddConnectionForm(category) +
                '</div>\n');
            adjacentProblemIconHTML = '<i class="fa fa-circle problem-icon ' + category + '-icon"></i>\n';
            endHTML = '</div>';
            renderedConnectionForm = (category == 'broader') ?
                begHTML + adjacentProblemNameHTML + adjacentProblemIconHTML + endHTML :
                begHTML + adjacentProblemIconHTML + adjacentProblemNameHTML + endHTML
        }
        connectionScroll.prepend(renderedConnectionForm);

        $('#submit-add-' + category + '-connection').on('click', function() {
            submitAddConnection(category);
        });
        $('#cancel-add-' + category + '-connection').on('click', function() {
            cancelAddConnection(category);
        });
        scrollTo('beginning', axis, connectionScroll);

        $('#' + category + '-problem-name-input').focus()
    }


    function renderNewRatedConnection(category, ratedConnectionPayload) {
        var rootKey = ratedConnectionPayload.root_key;
        var ratedConnection = ratedConnectionPayload[rootKey];
        var begHTML, adjacentProblemNameHTML, adjacentProblemIconHTML, endHTML;
        var renderedRatedConnection;
        var axis = deriveAxis(category);
        var connectionScroll = $('#' + category + '-scroll');

        if (axis == 'causal') {
            begHTML = '<div class="v-problem">\n';
            adjacentProblemNameHTML = (
                '<div class="v-problem-link-container v-align-inner word-break">\n' +
                    '<a href="' + ratedConnection.adjacent_community_uri + '" class="problem-link">' +
                        ratedConnection.adjacent_problem_name +
                        ' (' + ratedConnection.rating + ')\n' +
                    '</a>\n' +
                '</div>\n');
            adjacentProblemIconHTML = (
                '<div class="v-align-inner">\n' +
                    '<a href="' + ratedConnection.adjacent_community_uri + '">\n' +
                        '<i class="fa fa-circle problem-icon ' + category + '-icon"></i>\n' +
                    '</a>\n' +
                '</div>\n');
            endHTML = '</div>\n';
            renderedRatedConnection = (category == 'driver') ?
                begHTML + adjacentProblemNameHTML + adjacentProblemIconHTML + endHTML :
                begHTML + adjacentProblemIconHTML + adjacentProblemNameHTML + endHTML
        } else if (axis == 'scoped') {
            begHTML = '<div class="h-problem ' + category + '-problem">\n';
            adjacentProblemNameHTML = (
                '<div class="h-problem-link-container word-break">\n' +
                    '<a href="' + ratedConnection.adjacent_community_uri + '" class="problem-link">' +
                        ratedConnection.adjacent_problem_name +
                        ' (' + ratedConnection.rating + ')\n' +
                    '</a>\n' +
                '</div>\n');
            adjacentProblemIconHTML = (
                '<a href="' + ratedConnection.adjacent_community_uri + '">\n' +
                    '<i class="fa fa-circle problem-icon ' + category + '-icon"></i>\n' +
                '</a>\n');
            endHTML = '</div>\n';
            renderedRatedConnection = (category == 'broader') ?
                begHTML + adjacentProblemNameHTML + adjacentProblemIconHTML + endHTML :
                begHTML + adjacentProblemIconHTML + adjacentProblemNameHTML + endHTML
        }

        connectionScroll.append(renderedRatedConnection);

        scrollTo('end', axis, connectionScroll);
    }

    function submitAddConnection(category) {
        var adjacentProblemName = $('#' + category + '-problem-name-input').val();
        var axis = (category == 'driver' || category == 'impact') ? 'causal' : 'scoped';
        var problemA = (category == 'driver' || category == 'broader') ? adjacentProblemName : problem['name'];
        var problemB = (category == 'driver' || category == 'broader') ? problem['name'] : adjacentProblemName;

        var addConnectionPayload = {
            "connection": {
                "axis": axis,
                "problem_a": problemA,
                "problem_b": problemB
            },
            "community": {
                "problem": problem['human_id'],
                "org": null,
                "geo": geo['human_id']
            },
            "aggregation": "strict"
        };

        $.ajax({
            type: "POST",
            url: "http://localhost:5000/problems/rated_connections",
            data: JSON.stringify(addConnectionPayload),
            dataType: "json",
            contentType : "application/json",
            success: function(ratedConnectionPayload){
                renderNewRatedConnection(category, ratedConnectionPayload);
            } // TODO: Add failure handling
        });

        $('#add-' + category + '-connection-component').remove();
        isAddingConnection[category] = false;
    }

    function cancelAddConnection(category) {
        $('#add-' + category + '-connection-component').remove();
        isAddingConnection[category] = false;
    }

    $('#add-driver-connection').on('click', function() {
        renderAddConnectionFormContainer('driver');
    });

    $('#add-impact-connection').on('click', function() {
        renderAddConnectionFormContainer('impact');
    });

    $('#add-broader-connection').on('click', function() {
        renderAddConnectionFormContainer('broader');
    });

    $('#add-narrower-connection').on('click', function() {
        renderAddConnectionFormContainer('narrower');
    });
});