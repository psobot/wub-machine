(function() {
  var nonzero, parseSongs;
  nonzero = function(series) {
    var x, _i, _len;
    for (_i = 0, _len = series.length; _i < _len; _i++) {
      x = series[_i];
      if (x[1] !== 0) {
        return true;
      }
    }
    return false;
  };
  parseSongs = function(songs) {
    var data, name, types, _results;
    types = {
      'Finished': songs.remixTrue,
      'Failed': songs.remixFalse,
      'Shared': songs.shareTrue,
      'Failed Sharing': songs.shareFalse,
      'Downloaded': songs.download
    };
    _results = [];
    for (name in types) {
      data = types[name];
      _results.push({
        type: 'line',
        name: name,
        data: data,
        visible: nonzero(data)
      });
    }
    return _results;
  };
  window.updateGraph = function() {
    return $.getJSON("/monitor/graph", function(songs) {
      return createGraph(parseSongs(songs));
    });
  };
  window.createGraph = function(graphData) {
    return window.graph = new Highcharts.Chart({
      chart: {
        renderTo: 'songs',
        plotBackgroundColor: null,
        plotBorderWidth: null,
        plotShadow: false,
        zoomType: 'x',
        animation: false,
        events: {
          selection: function(e) {
            if (e.xAxis != null) {
              return $.get("/monitor/timespan", {
                start: e.xAxis[0].min / 1000,
                end: e.xAxis[0].max / 1000
              }, function(resp) {
                if (resp !== '') {
                  return $('#latest').slideUp(function() {
                    return $('#focus').html(resp).slideDown();
                  });
                }
              });
            } else {
              return $('#focus').slideUp(function() {
                $(this).html('');
                return $('#latest').slideDown();
              });
            }
          }
        }
      },
      title: {
        text: 'Logs & Stats for the Wub Machine'
      },
      xAxis: {
        type: 'datetime',
        tickInterval: 3600 * 1000 * 24,
        tickWidth: 0,
        gridLineWidth: 1,
        maxZoom: 6 * 3600000
      },
      yAxis: {
        title: {
          text: "Number of Songs"
        },
        min: 0
      },
      plotOptions: {
        line: {
          allowPointSelect: true
        },
        series: {
          cursor: 'pointer',
          point: {
            events: {
              select: function() {
                console.log(this.series.name);
                return console.log(this.category);
              },
              unselect: function() {
                return console.log(this.series.name);
              }
            }
          }
        }
      },
      series: graphData
    });
  };
  $(document).ready(function() {
    var s;
    s = new io.Socket(window.location.hostname, {
      port: window.wubconfig.socket_io_port,
      rememberTransport: window.wubconfig.remember_transport,
      resource: window.wubconfig.monitor_resource
    });
    s.connect();
    s.on("message", function(result) {
      var target;
      target = $("#" + $(result).attr('id'));
      if (target.length) {
        return target.replaceWith(result);
      } else {
        return $("#latest").prepend(result);
      }
    });
    updateGraph();
    return setInterval(updateGraph, 600000);
  });
}).call(this);
