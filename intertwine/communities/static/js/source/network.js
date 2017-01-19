
$(document).ready(function() {
    var payload = JSON.parse($('#payload').val());
    var rootKey = payload['root_key'];
    var community = payload[rootKey];
    var problemKey = community['problem']
    var problem = problemKey ? payload[problemKey]: null;
    var orgKey = community['org']
    var org = orgKey ? payload[orgKey]: null;
    var geoKey = community['geo']
    var geo = geoKey ? payload[geoKey]: null;

    $('#add-broader-problem').on('click', function() {
        $('#broader-scroll').prepend(
            '<div class="h-problem broader-problem">\n' +
                '<div class="h-problem-link-container word-break">\n' +
                    '<form id="add-broader-problem-form" action="add-broader-problem" method="post">\n' +
                        '<input id="add-broader-problem-name" type="text" name="add-broader-problem-name" maxlength="60" placeholder="Broader Problem"><br>\n' +
                        '<a href=# id="submit-add-broader-problem" class="submit-add-adjacent-problem-link"> Add </a>\n' +
                        '<a href=# id="cancel-add-broader-problem" class="cancel-add-adjacent-problem-link"> Cancel </a>\n' +
                    '</form>\n' +
                '</div>\n' +
                '<i class="fa fa-circle problem-icon broader-icon"></i>\n' +
            '</div>'
        );

        $('#submit-add-broader-problem').on('click', function() {
            var problemA = $('#add-broader-problem-name').val();
            var problemB = problem['name']

            var addBroaderProblemPayload = {
                "axis": "scoped",
                "problem_a_name": problemA,
                "problem_b_name": problem['name'],
                "community": {
                    "problem_human_id": problem['human_id'],
                    "org_human_id": null,
                    "geo_human_id": geo['human_id']
                }
            };
            console.log(addBroaderProblemPayload);

            $.ajax({
                type: "POST",
                url: "http://localhost:5000/problems/connections",
                data: JSON.stringify(addBroaderProblemPayload),
                success: function(){},
                dataType: "json",
                contentType : "application/json"
            });
        });
    });
});