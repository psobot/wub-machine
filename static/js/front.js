(function() {
  var addPlayer, counter, firsttitle, lastwidth, loaded, manualSeek, startCountdown, watch;
  manualSeek = false;
  loaded = false;
  addPlayer = function(filename) {};
  window.log = function() {
    log.history = log.history || [];
    log.history.push(arguments);
    if (typeof console !== "undefined" && console !== null) {
      return console.log(Array.prototype.slice.call(arguments));
    }
  };
  counter = 0;
  firsttitle = document.title;
  lastwidth = 0;
  $(document).ready(function() {
    $(".qq-upload-button").remove();
    window.beforeUpload = function(callback) {
      $(".progress").slideUp();
      return $("#file-uploader").slideUp(function() {
        $("#content").prepend("<div class='newlabel'></div><a href='#' class='style' id='style_Dubstep'>Dubstep</a><a href='#' class='style right' id='style_ElectroHouse'>Electro House</div>");
        $(".newlabel").fadeIn('slow');
        return $(".style").click(function() {
          $(".newlabel").fadeOut('slow');
          window.uploader._handler._options.extra_url_params = "&style=" + $(this).attr('id').split('_')[1];
          $(".style").slideUp();
          callback();
          return $(".progress").slideDown();
        });
      });
    };
    return window.uploader = new qq.FileUploader({
      element: document.getElementById("file-uploader"),
      action: "upload",
      allowedExtensions: window.wubconfig.allowed_file_extensions,
      debug: false,
      onSubmit: function(id, fileName) {
        $("#file-uploader").remove();
        $(".progress").show();
        $(".progress .text").show();
        $(".progress .text").html("Uploading song...");
        return document.title = "Uploading song...";
      },
      onProgress: function(id, fileName, loaded, total) {
        $(".progress").width(((loaded / total) * 100) + "%");
        return document.title = "Uploading: " + Math.round((loaded / total) * 100) + "%";
      },
      onComplete: function(id, fileName, r) {
        if (r.success) {
          $(".progress .text").show();
          $(".progress .text").html(r.text);
          $(".progress .number").show();
          window.wubconfig.uid = r.uid;
          $(".progress").width(0);
          document.title = "Waiting...";
          $(".link").slideDown();
          return watch(r.uid);
        } else {
          window.log("Something went wrong.", fileName, r);
          if (!r.response) {
            return $(".progress .text").html("Sorry, that song didn't work. Try another!");
          } else {
            return $(".progress .text").html("Hmm... something went wrong there. Try again!");
          }
        }
      },
      onCancel: function(id, fileName) {},
      showMessage: function(message) {
        var a;
        a = $(".qq-upload-button input");
        $(".qq-upload-button").html(message);
        return $(".qq-upload-button").append(a);
      }
    });
  });
  watch = function(uid) {
    var s;
    s = new io.Socket(window.location.hostname, {
      port: window.wubconfig.socket_io_port,
      resource: window.wubconfig.progress_resource + window.wubconfig.socket_extra_sep + uid,
      rememberTransport: window.wubconfig.remember_transport,
      reconnect: true
    });
    s.on('connection', function(data) {
      window.log("Socket opened, with data:");
      return window.log(data);
    });
    s.on('disconnect', function(data) {
      window.log("Socket closed, with data:");
      return window.log(data);
    });
    s.on('message', function(data) {
      var displayTag, html;
      $('.progress .text').html(data.text);
      switch (data.status) {
        case -1:
          $(".progress").animate({
            width: 0
          });
          window.log("Error", data);
          document.title = "Error!";
          return s.disconnect();
        case 0:
          return document.title = "Waiting...";
        case 1:
          $('.progress').animate({
            width: (data.progress * 100) + "%"
          });
          document.title = Math.round(data.progress * 100, 2) + "% - " + data.text;
          displayTag = (data.tag.title != null) && data.tag.title !== '';
          if (!$("#precontent").is(":visible")) {
            if (displayTag) {
              $("#precontent").html("Currently remixing <strong>" + data.tag.title + "</strong>" + (data.tag.artist != null ? " by " + data.tag.artist + "..." : void 0));
              $("#precontent").slideDown();
            }
          }
          if (data.progress === 1) {
            document.title = "Done!";
            html = "<div class='ui360 ui360-vis " + (!displayTag ? 'center' : void 0) + "'><a href='" + data.tag.remixed + "'></a></div>";
            if (data.tag.art != null) {
              html += "<div id='art'><img src='" + data.tag.thumbnail + "' alt='" + data.tag.album + "' title='wubwubwub!' /></div>";
            }
            if (displayTag) {
              html += "<div id='tag' class='trackviewer'><strong>" + data.tag.new_title + "</strong><br />by " + data.tag.artist + "<br />from <em>" + data.tag.album + "<em></div>";
            }
            html = "<div id='player'>" + html + "</div>";
            $(html).insertBefore('.progress');
            window.soundManager.reboot();
            $("#content").animate({
              border: 0
            });
            $("#post").slideDown();
            $(".error, #checkout, #precontent").slideUp(function() {
              return $(this).remove();
            });
            startCountdown();
            $(".progress").fadeOut(function() {
              return $("#player").slideDown();
            });
            $(".download a").attr("href", "download/" + data.uid);
            if (displayTag) {
              return document.title = data.tag.new_title;
            }
          }
      }
    });
    return s.connect();
  };
  startCountdown = function() {
    var interval, timeLeft;
    timeLeft = 30 * 60 * 1000;
    return interval = setInterval(function() {
      if (timeLeft <= 0) {
        clearInterval(interval);
        return $('.download, .soundcloud, .link').slideUp();
      } else {
        timeLeft -= 1000;
        return $('.link .smaller').html("This remix will be deleted in " + (parseInt(timeLeft / 60000)) + " minutes.");
      }
    }, 1000);
  };
}).call(this);
