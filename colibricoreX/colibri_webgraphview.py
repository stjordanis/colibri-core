#!/usr/bin/env python3

from __future__ import print_function, unicode_literals, division, absolute_import
import argparse
import cherrypy
import colibricore
import sys

def safe(s):
    return s.replace("'","`")


def processrelations(type, func, pattern, nodes, edges, classdecoder, colors, relationtypes=""):
    if not relationtypes or type in relationtypes:
        for pattern2, count in func(pattern):
            nodeid= safe(type + pattern2.tostring(classdecoder))
            if not pattern2 in nodes:
                nodes[nodeid] =  [nodeid, pattern2, count,type]
            edges.append( [nodeid, pattern, pattern2, type, count] )


class Root:
    def __init__(self, patternmodel, classdecoder, classencoder):
        self.patternmodel = patternmodel
        self.classdecoder = classdecoder
        self.classencoder = classencoder

    @cherrypy.expose
    def query(self, pattern, relationtypes=""):
        pattern = self.classencoder.buildpattern(pattern)
        nodes = {}
        nodes['center'] = ['center', pattern, self.patternmodel.occurrencecount(pattern),'center' ]
        edges = []

        minnodesize = 1
        maxnodesize = 10
        minedgesize = 1
        maxedgesize = 10

        colors = {'center':'#ff0000', 'c': "#222" , 'p': "#222",'r': "#32883c" ,'l': "#32883c",'t': '#323288' }
        extra = {'c': "arrow: 'target'",'p':"arrow: 'source'", 'l':  "arrow: 'source'" ,'r':  "arrow: 'target'", 't': "arrow: 'source'"}

        processrelations('c',self.patternmodel.getsubchildren, pattern, nodes, edges, self.classdecoder, colors, relationtypes)
        processrelations('p',self.patternmodel.getsubparents, pattern, nodes, edges, self.classdecoder,  colors,relationtypes)
        processrelations('l',self.patternmodel.getleftneighbours, pattern, nodes, edges, self.classdecoder,  colors,relationtypes)
        processrelations('r',self.patternmodel.getrightneighbours, pattern, nodes, edges,self.classdecoder,  colors,relationtypes)
        processrelations('t',self.patternmodel.gettemplates, pattern, nodes, edges,self.classdecoder,  colors,relationtypes)

        jscode = "var sigRoot = document.getElementById('graph');\nsigInst = sigma.init(sigRoot);"
        jscode += "sigInst.drawingProperties({ defaultLabelColor: '#222', defaultLabelSize: 14, defaultLabelHoverColor: '#000', labelThreshold: 6, font: 'Arial', edgeColor: 'source', defaultEdgeType: 'curve' });\n"
        jscode += "sigInst.graphProperties({ minNodeSize: " + str(minnodesize) + ", maxNodeSize: " + str(maxnodesize) + ", minEdgeSize: " + str(minedgesize) + ", maxEdgeSize: " + str(maxedgesize) + " });\n"
        jscode += "sigInst.mouseProperties({ maxRatio: 450, minRatio: .1, marginRatio: 1, zoomDelta: 0.1, dragDelta: 0.3, zoomMultiply: 1.5, inertia: 1.1 });\n"



        for nodeid, p, count, type in nodes.values():
            s = safe(p.tostring(self.classdecoder))
            size = count #add normalisation here!
            color = colors[type]
            #if p == pattern:
            #    color = "#ff0000"
            #elif p.isskipgram():
            #    color = "#0000ff"
            #elif p.isflexgram():
            #    color = "#00ff00"
            #else:
            #    color = "#000000"

            jscode += "sigInst.addNode('" +  nodeid + "',{label: '" + s + " (" + str(count) + ")', 'size':"+str(size)+",'cluster': '" + type + "', 'color': '" + color + "', 'x': Math.random(),'y': Math.random() });\n"

        for nodeid, frompattern,topattern, type, count in edges:
            s_from = 'center'
            s_to = nodeid
            s_edgeid = s_from + "_REL" + type + "_" + s_to
            color = colors[type]
            if type in extra:
                e = ", " + extra[type]
            else:
                e = ""
            size = count #add normalisation here!
            jscode += "sigInst.addEdge('" + s_edgeid + "', '" +s_from  + "','" +s_to  + "' ,{'size':" + str(size) + ", 'color':'" + color + "'" + e + "});\n"
            jscode += "sigInst.draw();\n"
            jscode += "sigInst.startForceAtlas2();\n"
            jscode += "window.setTimeout(function(){ sigInst.stopForceAtlas2();}, 5000);\n";


        jscode = "$(document).ready(function(){" + jscode + "});"


        html = "<html><head><title>Colibri PatternGraphView</title>"
        html += "<meta charset=\"utf-8\">"
        html += "<script src=\"http://sigmajs.org/js/sigma.min.js\"></script>"
        html += "<script src=\"http://sigmajs.org/js/sigma.forceatlas2.js\"></script>"
        html += "<script src=\"http://code.jquery.com/jquery-1.10.1.min.js\"></script>"
        html += "</head>"
        html += "<script type=\"text/javascript\">" + jscode + "</script>"
        html += "<body><div id=\"graph\" style=\"width: 90%; height:90%; \"></div><form action=\"/query/\" method=\"post\"><input name=\"pattern\" /><input type=\"submit\"></form></body></html>";
        return html

    @cherrypy.expose
    def index(self):
        html = "<html><head><title>Colibri PatternGraphView</title>"
        html += "<meta charset=\"utf-8\">"
        html += "<script src=\"http://sigmajs.org/js/sigma.min.js\"></script>"
        html += "<script src=\"http://sigmajs.org/js/sigma.forceatlas2.js\"></script>"
        html += "<script src=\"http://code.jquery.com/jquery-1.10.1.min.js\"></script>"
        html += "</head>"
        html += "<body><div id=\"graph\"></div><form action=\"/query/\" method=\"post\"><input name=\"pattern\" /><input type=\"submit\"></form></body></html>";
        return html




def main():
    parser = argparse.ArgumentParser(description="", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i','--input', type=str,help="The Indexed Pattern Model to load", action='store',required=True)
    parser.add_argument('-c','--classfile', type=str,help="The class file", action='store',required=True)
    args = parser.parse_args()

    print("Loading class encoder",file=sys.stderr)
    classencoder = colibricore.ClassEncoder(args.classfile)
    print("Loading class decoder",file=sys.stderr)
    classdecoder = colibricore.ClassDecoder(args.classfile)
    print("Loading pattern model",file=sys.stderr)
    patternmodel = colibricore.IndexedPatternModel(args.input)

    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8080,
    })
    cherrypy.quickstart(Root(patternmodel, classdecoder, classencoder))

if __name__ == '__main__':
    main()