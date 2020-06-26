class Convert {

    getSelectedSessions() {

        var selectedSessionData = [];
        $('#session_choice tbody input[type="checkbox"]').each(function (i, it) {
            var $it = $(it);
            if ($it.prop("checked")) {
                var tr = $it.parent().parent();
                var session_data = tr.data('subj_date_path');

                var new_subject_id = tr.find('input.new_subjectid').val();
                //the input field in this row would only exist if the user edited it.
                //also if the user did initiate an edit but currently has provided no
                //value for a new subject id we just preserve the original subject id

                //so we only add the new_subject_id to the payload if the user has edited
                // subjected and provided a value for it
                if (new_subject_id) {
                    session_data = session_data.slice(); //clone the array so we preserve the original subjectid here in the local state

                    //but replace the subjectid in the data to be pushed to the server
                    session_data[0] = new_subject_id;
                }

                selectedSessionData.push(session_data);

            }

        });

        return selectedSessionData;
    }
}


$("#check_all").click(function () {
    $("#search_selection option").prop('selected', true)
})

$("#uncheck_all").click(function () {
    $("#search_selection option").prop('selected', false)
})
