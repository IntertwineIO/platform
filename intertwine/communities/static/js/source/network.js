
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

    var isAddingBroaderProblem = false;

    $('#add-broader-problem').on('click', function() {
        if (isAddingBroaderProblem) {
            return;
        }
        isAddingBroaderProblem = true;

        $('#broader-scroll').prepend(  // TODO: move to AddBroaderProblem component
            '<div id="add-broader-problem-component" class="h-problem broader-problem">\n' +
                '<div class="h-problem-link-container word-break">\n' +
                    '<form id="add-broader-problem-form" action="add-broader-problem" method="post">\n' +
                        '<input id="add-broader-problem-name" type="text" name="add-broader-problem-name" maxlength="60" placeholder="Broader Problem" autofocus><br>\n' +
                        '<a href=# id="submit-add-broader-problem" class="submit-add-adjacent-problem-link"> Add </a>\n' +
                        '<a href=# id="cancel-add-broader-problem" class="cancel-add-adjacent-problem-link"> Cancel </a>\n' +
                    '</form>\n' +
                '</div>\n' +
                '<i class="fa fa-circle problem-icon broader-icon"></i>\n' +
            '</div>'
        );

        function renderNewBroaderConnection(ratedConnectionPayload) {
            console.log(ratedConnectionPayload);
            var rootKey = ratedConnectionPayload.root_key;
            var ratedConnection = ratedConnectionPayload[rootKey];

            $('#broader-scroll').append(
                '<div class="h-problem broader-problem">' +
                    '<div class="h-problem-link-container word-break">' +
                        '<a href="' + ratedConnection.adjacent_community_uri + '" class="problem-link">' +
                            ratedConnection.adjacent_problem_name +
                            ' (' + ratedConnection.rating + ')' +
                        '</a>' +
                    '</div>' +
                    '<a href="' + ratedConnection.adjacent_community_uri + '">' +
                        '<i class="fa fa-circle problem-icon broader-icon"></i>' +
                    '</a>' +
                '</div>'
            );
        }

        $('#submit-add-broader-problem').on('click', function() {
            var problemA = $('#add-broader-problem-name').val();

            var addBroaderProblemPayload = {
                "connection": {
                    "axis": "scoped",
                    "problem_a": problemA,
                    "problem_b": problem['name']
                },
                "community": {
                    "problem": problem['human_id'],
                    "org": null,
                    "geo": geo['human_id']
                },
                "aggregation": "strict",
                "rating": -1,
                "weight": 0
            };
            console.log(addBroaderProblemPayload);

            $.ajax({
                type: "POST",
                url: "http://localhost:5000/problems/rated_connections",
                data: JSON.stringify(addBroaderProblemPayload),
                dataType: "json",
                contentType : "application/json",
                success: function(ratedConnectionPayload){
                    renderNewBroaderConnection(ratedConnectionPayload);
                } // Add new connection and feedback message
            });

            $('#add-broader-problem-component').remove()
            isAddingBroaderProblem = false;
        });

        $('#cancel-add-broader-problem').on('click', function() {
            $('#add-broader-problem-component').remove()
            isAddingBroaderProblem = false;
        });
    });
});