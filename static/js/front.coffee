manualSeek = false
loaded = false

addPlayer = (filename) ->

window.log = ->
  log.history = log.history or []
  log.history.push arguments
  console.log Array::slice.call(arguments) if console?

counter = 0
firsttitle = document.title
lastwidth = 0

$(document).ready ->
  $(".qq-upload-button").remove()
  window.beforeUpload = (callback) ->
    $(".progress").slideUp()
    $("#file-uploader").slideUp ->
      $("#content").prepend "<div class='newlabel'></div><a href='#' class='style' id='style_Dubstep'>Dubstep</a><a href='#' class='style right' id='style_ElectroHouse'>Electro House</div>"
      $(".newlabel").fadeIn('slow')
      $(".style").click ->
        $(".newlabel").fadeOut('slow')
        window.uploader._handler._options.extra_url_params = ("&style=" + $(this).attr('id').split('_')[1])
        $(".style").slideUp()
        callback()
        $(".progress").slideDown()
  window.uploader = new qq.FileUploader(
    element: document.getElementById("file-uploader")
    action: "upload"
    allowedExtensions: window.wubconfig.allowed_file_extensions
    debug: false
    onSubmit: (id, fileName) ->
      $("#file-uploader").remove()
      $(".progress").show()
      $(".progress .text").show()
      $(".progress .text").html "Uploading song..."
      document.title = "Uploading song..."
    
    onProgress: (id, fileName, loaded, total) ->
      $(".progress").width ((loaded / total) * 100) + "%"
      document.title = "Uploading: " + Math.round((loaded / total) * 100) + "%"
    
    onComplete: (id, fileName, r) ->
      if r.success
        $(".progress .text").show()
        $(".progress .text").html r.text
        $(".progress .number").show()
        window.wubconfig.uid = r.uid
        $(".progress").width 0
        document.title = "Waiting..."
        $(".link").slideDown()
        watch r.uid
      else
        window.log "Something went wrong.", fileName, r
        unless r.response
          $(".progress .text").html "Sorry, that song didn't work. Try another!"
        else
          $(".progress .text").html "Hmm... something went wrong there. Try again!"
    
    onCancel: (id, fileName) ->
    
    showMessage: (message) ->
      a = $(".qq-upload-button input")
      $(".qq-upload-button").html message
      $(".qq-upload-button").append a
  )

watch = (uid) ->
  s = new io.Socket window.location.hostname, {
    port: window.wubconfig.socket_io_port,
    resource: window.wubconfig.progress_resource + window.wubconfig.socket_extra_sep + uid,
    rememberTransport: window.wubconfig.remember_transport,
    reconnect: true
  }

  s.on 'connection', (data) ->
    window.log "Socket opened, with data:"
    window.log data

  s.on 'disconnect', (data) ->
    window.log "Socket closed, with data:"
    window.log data

  s.on 'message', (data) ->
    $('.progress .text').html data.text
    switch data.status
      when -1 # error has occurred
        $(".progress").animate width: 0
        window.log "Error", data
        document.title = "Error!"
        s.disconnect()
      when 0 # waiting
        document.title = "Waiting..."
      when 1 # remixing
        $('.progress').animate width: (data.progress * 100) + "%"
        document.title = Math.round(data.progress * 100, 2) + "% - " + data.text
        displayTag = data.tag.title? and data.tag.title != ''
        unless $("#precontent").is(":visible")
          if displayTag
            $("#precontent").html "Currently remixing <strong>" + data.tag.title + "</strong>" + (" by " + data.tag.artist + "..." if data.tag.artist?)
            $("#precontent").slideDown()

        if data.progress == 1
          # We're done remixing, present the track to the user
          document.title = "Done!"

          # Adding and getting rid of visual elements 'n such

          # Metadata display
          html = "<div class='ui360 ui360-vis #{'center' unless displayTag}'><a href='#{data.tag.remixed}'></a></div>"
          if data.tag.art?
            html += "<div id='art'><img src='#{data.tag.thumbnail}' alt='#{data.tag.album}' title='wubwubwub!' /></div>"
          if displayTag
            html += "<div id='tag' class='trackviewer'><strong>#{data.tag.new_title}</strong><br />by #{data.tag.artist}<br />from <em>#{data.tag.album}<em></div>"
          html = "<div id='player'>#{html}</div>"
          $(html).insertBefore '.progress'

          window.soundManager.reboot()
          $("#content").animate {border: 0}
          $("#post").slideDown()
          $(".error, #checkout, #precontent").slideUp ->
            $(this).remove()
          startCountdown()
          $(".progress").fadeOut ->
            $("#player").slideDown()
                    
          # Set download link and title of page
          $(".download a").attr "href", "download/" + data.uid
          document.title = data.tag.new_title if displayTag

  s.connect()

startCountdown = ->
  timeLeft = 30*60*1000
  interval = setInterval ->
    if timeLeft <= 0
      clearInterval(interval)
      $('.download, .soundcloud, .link').slideUp()
    else
      timeLeft -= 1000
      $('.link .smaller').html "This remix will be deleted in #{parseInt(timeLeft/60000)} minutes."
  , 1000
