$(document).ready( initializeForm );

function initializeForm() {

    // Start out by clearing the To Do input
    $("#todo_input").val("");

    // Define what happens when we click the "Add Item" link
    $("#add-item").click( addItem );

    // Define what happens when we press the enter key on the to do input.
    $("#todo_input").keypress(function(e){
        if(e.which==13) { e.preventDefault(); addItem(); }
    });


    // the items list will be sortable.
    $( "ul#items" ).sortable({
        update: function( event, ui ) {
            UpdateOrder($(this).sortable('toArray'));
        }
    }).disableSelection();

    // populate the to do list with all the tasks in the database
    LOADTASKS();
}

function UpdateOrder(array)
{
    // build a specially-formatted string and send over the new order to the server
    var item_to_send = {
        text: array.toString()
    };

    $.ajax(
        {
            type: "POST",
            url: 'todo/update_order',
            data: $.param(item_to_send),
            dataType: "text"
        }
    );
}

function addItem() {

    // get user input
    var itemTitle = $("#todo_input").val();

    // return on no input
    if (itemTitle == '')
        return;

    // create a list item initially hidden, assigning an id to it. add a way to remove it.
    $listItem = AppendItem( itemTitle, 0 );

    // add this item to the database, filling in its id field with the id given by the database
    ADDtoDATABASE($listItem);

    // clear the input box
    $("#todo_input").val("");
}

function AppendItem( itemTitle, itemId) {
    // build checkbox
    var checkbox = "<input type='button' value=' X ' id='checker' style='float: right'/>";

    var showcal = "<img src ='http://amilimani.com/wp-content/gallery/islamic-kingdom/united-states-of-america.jpg' width='36px;' height='24px;' class='calCheck' style='float: left;' />";
    var cal = "<input type='checkbox' class='calButton'  style=' float: left; margin-right:10px; position:left;'/>";

    // build list item, add an id (which may be a placeholder, hide it
    var $listItem = $("<li class='ui-state-default'> " + itemTitle + checkbox + cal + showcal + "</li>");
    $listItem.attr('id', itemId);
    $listItem.hide();
    $listItem.find(".calButton").hide();

    $listItem.find(".calCheck").bind('mousedown', function() {
       $listItem.find(".calButton").show();
    });
    $listItem.find(".calCheck").bind('doubleclick', function() {
        $listItem.find(".calButton").hide();
    });

    $listItem.find(".calButton").bind('click', function() {
        if($(this).is(':checked'))
        {
            alert("hello")
            $(this).parent().draggable({
            zIndex: 999,
            revert: true,      // will cause the event to go back to its
            revertDuration: 0  //  original position after the drag
            });
        }
        else
            {
                $(this).parent().draggable( "option", "disabled", true );
            }
    });

//  remove the corresponding list item when remove is clicked, and update the TaskManager to store the new order
    $listItem.find("#checker").click( function() {
        REMOVEfromDATABASE($(this).parent().attr("id"));
        $(this).parent().hide('slow', function() {
            $(this).remove();
            UpdateOrder($("ul#items").sortable('toArray'));
        });
    });

    // add item to DOM and show it
    $("ul#items").append( $listItem );
    $listItem.show('slow');

    return $listItem;
}

function LOADTASKS()
{
    $.ajax(
        {
            type:"GET",
            url:'todo/get_tasks',
            dataType: "json",
            success: function (data)
            {
                // add tasks to todo_ list
                JSONtoTASKS(data);
            }
        }
    );
}


function JSONtoTASKS(json)
{
    $.ajax(
        {
            type:"GET",
            url:'todo/get_order',
            dataType: "json",
            success: function (data)
            {
                // get the order of elements as an array
                csv_order = data[0]["fields"]["order"];
                order = csv_order.split(',');

                // for each element of the order array, pick out the task with that id and render it
                for (var i = 0, n = order.length; i < n; i++)
                {
                    for (index in json)
                    {
                        task = json[index];
                        if (task["pk"] == order[i])
                            AppendItem(task["fields"]["title"], task["pk"]);
                    }
                }
            }
        }
    );
}

function ADDtoDATABASE($listItem)
{
    var item_to_send = {
        title: $listItem.text()
        // todo add a date
    };
    $.ajax(
        {
            type: "POST",
            url: 'todo/add_task',
            data:$.param(item_to_send),
            dataType: "text",
            success: function (data){
                $listItem.attr('id', data);
                // now that this id has gone through, update the database ordering
                UpdateOrder($( "ul#items" ).sortable('toArray'));
            }
        }
    )
}


function REMOVEfromDATABASE(id_to_delete)
{
    var item_to_send = {
        id: id_to_delete
        // todo add a date
    };
    $.ajax(
        {
            type: "POST",
            url: 'todo/remove_task',
            data: $.param(item_to_send),
            dataType: "text"
        }
    )
}