nonzero = (series) ->
  for x in series
    if x[1] != 0
      return true
  return false

parseSongs = (songs) ->
  types =
    'Finished': songs.remixTrue
    'Failed': songs.remixFalse
    'Shared': songs.shareTrue
    'Failed Sharing': songs.shareFalse
    'Downloaded': songs.download
  {type: 'line', name: name, data: data, visible: (nonzero(data))} for name, data of types

window.updateGraph = ->
  $.getJSON("/monitor/graph", (songs) -> createGraph parseSongs(songs))

window.createGraph = (graphData) ->
  window.graph = new Highcharts.Chart
    chart:
      renderTo: 'songs',
      plotBackgroundColor: null
      plotBorderWidth: null
      plotShadow: false
      zoomType: 'x'
      animation: false
      events:
        selection: (e) ->
          if e.xAxis? # We have zoomed in
            $.get "/monitor/timespan",
              { start: e.xAxis[0].min / 1000, end: e.xAxis[0].max / 1000 }
              (resp) ->
                if resp != ''
                  $('#latest').slideUp ->
                    $('#focus').html(resp).slideDown()
          else  # We have zoomed out
            $('#focus').slideUp ->
              $(this).html('')
              $('#latest').slideDown()
    title:
      text: 'Logs & Stats for the Wub Machine'
    xAxis:
      type: 'datetime',
      tickInterval: 3600 * 1000 * 24
      tickWidth: 0
      gridLineWidth: 1
      maxZoom: 6 * 3600000
    yAxis:
      title:
        text: "Number of Songs"
      min: 0
    plotOptions:
      line:
        allowPointSelect: true
      series:
        cursor: 'pointer'
        point:
          events:
            select: ->
              console.log this.series.name  #type
              console.log this.category #timestamp
            unselect: ->
              console.log this.series.name
    series: graphData

$(document).ready( ->
  s = new io.Socket(window.location.hostname,
    port: window.wubconfig.socket_io_port
    rememberTransport: window.wubconfig.remember_transport
    resource: window.wubconfig.monitor_resource
  )
  s.connect()
  s.on "message", (result) ->
    target = $("#" + $(result).attr('id'))
    if target.length
      target.replaceWith(result)
    else
      $("#latest").prepend(result)

  updateGraph()
  setInterval updateGraph, 600000
)


