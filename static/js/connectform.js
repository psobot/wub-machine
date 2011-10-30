SC.connectForm({
    size:         "s",
    client_id:    window.wubconfig.soundcloud_consumer,
    redirect_uri: window.wubconfig.soundcloud_redirect,
    flow:         "token",
    connected: function(){
        $("#cwsw-connect.cwsc-connect").html("<img src='static/img/ajax-small.gif' alt='Uploading...' title='Uploading...' /> Sharing...");
        $.getJSON("share/"+window.wubconfig.uid, { 'token': SC.options.access_token }, function(a){
            if(!!a.permalink_url){
                $("#cwsw-connect.cwsc-connect").addClass("withtext");
                $("#cwsw-connect.cwsc-connect").html("Remix shared!<span>Click to view on SoundCloud.</span>");
                $("#cwsw-connect.cwsc-connect").click(function(){
                    window.open( a.permalink_url );	//should be less dirty, need to rebind click handler and such...
                });
                SC.disconnect()
                SC.connect = function(){}
            } else {
                $("#cwsw-connect.cwsc-connect").html("Error... try again?");
            }
        });
    },
    disconnected: function(){
       window.log("Disconnected from SoundCloud.");
    }
});
$("#cwsw-connect.cwsc-connect").html("Share on SoundCloud");

