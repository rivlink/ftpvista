function addSearchProvider(){
    window.external.AddSearchProvider(ftpvista.search_engine_url);
}

function getResults(term, os, ft, page){
    page = parseInt(page, 10);
    $.post(
        ftpvista.results_url,
        {
            s: term,
            os: os,
            ft: ft,
            page: page
        },
        function(data){
            $("#search_result .results").html(data);
            if (page > 1){
                $(".prev").data("page", page-1)
            }
            if ($(".is_last_page").length === 0){
                $(".next").data("page", page+1)
            }
        }
    );
}

function getSearchTerm(){
}

function getOnline(){
}

function getFilters(){
}

function getPage(){
}

function previousPage(){
    getResults();
}

function nextPage(){
    getResults();
}

$(document).ready(function() {
    //Create tabs
    $("#tabs").tabs({
        create: function (event, ui) {
            if (window.location.hash.length > 0){
                $(this).tabs("option", "active", $(this).find("ul.tabs li").index($(this).find('a[href="' + window.location.hash + '"]').parent()));
            }else if(window.location.pathname.indexOf('/last') > -1){
                $(this).tabs("option", "active", -1); //select last tab
            }
        },
        beforeActivate: function (event, ui) {
            window.location.hash = ui.newPanel.selector;
        }
    });

    //Make the use of previous/next navigator buttons actually change active tab
    $(window).on('hashchange', function(){
        $('#tabs').tabs("option", "active", $('#tabs ul.tabs li').index($('#tabs a[href="' + window.location.hash + '"]').parent()));
    });

    //Show/hide advanced option pane in each tab
    $(".plus_sign").click(function(){
        var sTxt = ' Filtres';
        var cur_pane = $(this);
        cur_pane.next(".advanced_pane").toggle("fast");
        if (cur_pane.html().indexOf('+') != -1)
            cur_pane.html("-" + sTxt);
        else
            cur_pane.html("+" + sTxt);
        //To avoid the execution of the # in the href
        return false;
    });
    
    if (window.external){
        if ('AddSearchProvider' in window.external) {
            $("#summary").append("<span style=\"float:right;\"><a title=\"Add me !\" href=\"javascript:addSearchProvider();\">FTPVista dans ton navigateur !</a></span>")
        }
    }
    
    // Make visible a clicked row
    $("#browser tbody tr").mousedown(function() {
        $("tr.ui-state-highlight").removeClass("ui-state-highlight"); // Deselect currently selected rows
        $(this).addClass("ui-state-highlight");
    });

    // Make sure row is selected when span is clicked
    $("#browser tbody tr span").mousedown(function() {
        $(this).parents("tr:first").trigger("mousedown");
    });

    //Custom Multiselect
    $(".ft").multiselect({
        checkAllText: 'Tous',
        uncheckAllText: 'Aucun',
        noneSelectedText: 'Tous les fichiers',
        selectedList: 5,
        height: 'auto',
        minWidth: 345
    });

    // Refresh server statuses in ajax
    var checkservers = function(){
        $.post(
            ftpvista.online_url,
            function(data){
                $("#server-list").html(data);
            }
        );
        setTimeout(checkservers, 120000); //every 2 minutes
    };
    setTimeout(checkservers, 120000);
});
