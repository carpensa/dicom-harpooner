function check_required(bids_spec_json) {
    /**
     * This function checks whether or not the label
     * chosen bids label requires a prefix for.
     * e.g.: a 'bold' scan would require the prefix 'task-'
     * or an 'epi' scan would require 'dir-'
     * if scans don't require a certain label then this
     * function will return an empty string.
     * Otherwise it will return the required prefix.
     */
    if (bids_spec_json.required[bids_spec_json.choice]) {
        //console.log(label, bids_spec_json.required[label]);
        return bids_spec_json.required[bids_spec_json.choice]
    } else {
        return ""
    }
}

function check_optional(bids_spec_json) {
    if (bids_spec_json.optional[bids_spec_json.choice]){
        console.log(bids_spec_json.optional[bids_spec_json.choice]);
        return bids_spec_json.optional[bids_spec_json.choice]
    } else {
        return ""
    }
}

function hide_if_ignore(bids_spec_json) {
    /**
     * This function hides the required inputs if the scan type that is
     * selected is IGNORE and shows the fields if it isn't.
     */
    if (bids_spec_json.choice == "IGNORE") {
        $("#" + bids_spec_json['series'] + " .required_label .required_label").hide();
        $("#" + bids_spec_json['series'] + " .custom_label .custom_label").hide()
    } else if(bids_spec_json.choice == "epi" || bids_spec_json.choice == "bold") {
        //$("#" + bids_spec_json['series'] + " .required_label .required_label").prop("readonly", true)
        $("#" + bids_spec_json['series'] + " .required_label .required_label").show();
        $("#" + bids_spec_json['series'] + " .custom_label .custom_label").show()
    } else {
       // $("#" + bids_spec_json['series'] + " .required_label .required_label").show()
        $("#" + bids_spec_json['series'] + " .custom_label .custom_label").show()
    }
}


let formInfo = {};
$(document).on('change', 'td', function () {
    /**
     * This function collects all of the info that the user provides to
     * build a conversion form for dcm2bids. It will then convert that
     * information into a json to be passed back to django and stored
     * in the database using the DcmToBidsJson from dicoms.models
     *
     * For ease of use (although I'm not sure if it's best practice) and to
     * minimize the number of element selections the required info is stored
     * and hidden in div elements under the custom_label element in the
     * conversion form builder.
     */

    $(".scan").each(function (i, obj) {
        // getting all elements from custom label that have data
        let wrapper = this.className;
        let id = String(this.id);
        //console.log(id)
        //console.log("#" + id + " .modality")


        let series = $("#" + id + " .series").text();
        $("#" + id + " .collected_fields > .series").val(series);
        let modality = $("#" + id + " .modality").find(":selected").text();
        $("#" + id + " .collected_fields > .modality").val(modality);
        let required_label = $("#" + id + " .required_label .required_label").val();
        $("#" + id + " .collected_fields > .required_label").val(required_label);
        let custom_label = $("#" + id + " .custom_label .custom_label").val();
        $("#" + id + " .collected_fields > .custom_label").val(custom_label);
        /**console.log("series: ", series)
         console.log("modality: ", modality)
         console.log("required_label: ", required_label)
         console.log("custom_label", custom_label)
         */
        let test = {
            "series_id": id,
            "modality": modality,
            "required_label": required_label,
            "custom_label": custom_label
        };
        formInfo[series] = test


    });
    console.log(formInfo)
});
$("input[name=generate_convert_file]").click(function () {
    console.log($("div[name=create_conversion_file]").text())
});

$(document).on("change", "input", function f() {

    let create_new = $('#make_new_checkbox').is(':checked');
    if (create_new) {
        // show conversion builder
        // hide load previous config file
        $("#build_conversion_file").show();
        $(".build_conversion_file").show();
        $("#reuse_conversion_file").hide();
        $("#make_new_boolean").val("True")
    } else {
        // hide conversion builder
        // show load previous config file
        $("#build_conversion_file").hide();
        $(".build_conversion_file").hide();
        $("#reuse_conversion_file").show();
        $("#make_new_boolean").val("False")
    }
});

