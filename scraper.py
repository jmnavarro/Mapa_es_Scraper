#!/usr/bin/python
# coding: utf-8
import sys
import json
import re
import codecs
from mechanize import Browser


def get_browser():
    # Browser
    br = Browser()

    # Cookie Jar
    #cj = cookielib.LWPCookieJar()
    #br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    #br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # Want debugging messages?
    #
    #br.set_debug_http(True)
    #br.set_debug_redirects(True)
    #br.set_debug_responses(True)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    return br


def get_all_matchs(str, regexp):
    list = []
    expr = re.compile(regexp)
    hasMore = True
    startpos = 0
    while hasMore:
        match = expr.search(str, startpos)
        hasMore = (match != None)
        if hasMore:
            g = match.groups()
            if regexp.count('(') == 1:
                item = g[0]
            else:
                item = (g[0], g[1])
            list.append(item)
            startpos = match.end()
    return list


def parse_formulado_page(html, nomFormulado):
    expr = re.compile('No existen datos para la consulta realizada')
    if expr.search(html) != None:
        print "      Sin datos"
        return None

    expr = re.compile('href="/agricultura/pags/fitos/registro/productos/pdf/\d*.pdf".*>(\d*)</a>')
    match = expr.search(html)
    num_reg = match.groups()[0]

    nombres = get_all_matchs(html, '<td class="colu1_tabla">\s*<span.*tabla_texto_normal.*>(.*)</span>\s*</td>')
    for n in nombres:
        if n != nomFormulado:
            nombre = n
    
    expr = re.compile('<a.*href="/es/agricultura/pags/fitos/registro/titular/tit.asp\?id=\d*".*>(.*)</a>')
    match = expr.search(html)
    titular = match.groups()[0]

    num_reg = num_reg.decode("iso-8859-15").encode("utf-8")
    nombre = nombre.decode("iso-8859-15").encode("utf-8")
    nomFormulado = nomFormulado.decode("iso-8859-15").encode("utf-8")
    titular = titular.decode("iso-8859-15").encode("utf-8")

    print "      Data = num_registro=%(num_registro)s nombre=%(nombre)s formulado=%(formulado)s titular=%(titular)s" % {'num_registro' : num_reg, 'nombre' : nombre, 'formulado' : nomFormulado, 'titular' : titular}
    return {'num_registro' : num_reg, 'nombre' : nombre, 'formulado' : nomFormulado, 'titular' : titular}


def parse_ferti_result_page(html, tipo, list):
    expr_cod = re.compile('<a.*>(F\d*/\d*).*</a>')
    expr_nombre = re.compile('<td.*class="colu1_tabla".*>\s*<span>\s*<a.*href="DetalleFertilizante.aspx\?clave=\d*".*>(.*)<br><br></a>\s*</span>\s*</td>')
    expr_fabricante = re.compile('<a.*href="DetalleFabricante.aspx\?clave=\d*".*>(.*)<br><br></a>')
    expr_registro = re.compile('<td.*class="colu1_tabla".*>\s*<span.*class="tabla_texto_normal".*>(\d{2}/\d{2}/\d{4})</span>\s*</td>')

    startpos = 0
    while startpos >= 0:
        match = expr_cod.search(html, startpos)
        if match != None:
            cod = match.groups()[0]

            match = expr_nombre.search(html, startpos)
            nombre = match.groups()[0]

            match = expr_fabricante.search(html, startpos)
            fabricante = match.groups()[0]

            match = expr_registro.search(html, startpos)
            registro = match.groups()[0]

            cod = cod.decode("iso-8859-15").encode("utf-8")
            tipo_dec = tipo.decode("iso-8859-15").encode("utf-8")
            nombre = nombre.decode("iso-8859-15").encode("utf-8")
            fabricante = fabricante.decode("iso-8859-15").encode("utf-8")
            #registro = registro.decode("iso-8859-15").encode("utf-8")
            registro = "%s-%s-%s" % (registro[6:], registro[3:5], registro[:2])

            print "      Data = cod=%(cod)s tipo=%(tipo)s nombre=%(nombre)s fabricante=%(fabricante)s registro=%(fabricante)s" % {'cod' : cod, 'tipo' : tipo_dec, 'nombre' : nombre, 'fabricante' : fabricante, 'registro' : registro}
            list.append({'cod' : cod, 'tipo' : tipo_dec, 'nombre' : nombre, 'fabricante' : fabricante, 'registro' : registro})

            startpos = match.end()
        else:
            startpos = -1


def parse_ferti_search_result(html, tipo, cod, list):
    expr = re.compile('No se ha encontrado')
    if expr.search(html) != None:
        print "      Sin datos"
        return None


    expr = re.compile('Registros del \d* al (\d*) de los (\d*) encontrados.')
    match = expr.search(html)
    actual = match.groups()[0]
    final = match.groups()[1]

    parse_ferti_result_page(html, tipo, list)
    pageno = 1
    while actual < final:
        print "      Page %d..." % pageno

        page = get_browser()
        page.open('http://www.mapa.es/app/consultafertilizante/ListadoFertilizantes.aspx?TipoProducto=%s&Page=%s' % (cod, pageno))
        try:
            html = page.response().read()
            parse_ferti_result_page(html, tipo, list)
        finally:
            page.close()

        pageno = pageno + 1

        expr = re.compile('Registros del \d* al (\d*) de los (\d*) encontrados.')
        match = expr.search(html)
        actual = match.groups()[0]
        final = match.groups()[1]



def parse_fito_result_page(html, list):
    results = get_all_matchs(html, '"/es/agricultura/pags/fitos/registro/productos/proexi.asp\?IdFormulado=(\d*)".*>(.*)</a>')
    print ("Found %d" % len(results))

    if len(results) > 0:
        expr = re.compile('<div.*class="normal2b".*>\s*<br>Se han encontrado \d* registros. \(Página \d* de (\d*)\)')
        match = expr.search(html)
        if match != None:
            print("%s pages NOT SUPPORTED!!" % march.groups()[0])
            exit()

    for tuplas in results:
        idFormulado = tuplas[0]
        nomFormulado = tuplas[1]
        formulado = get_browser()
        formulado.open('http://www.mapa.es/es/agricultura/pags/fitos/registro/productos/proexi.asp?IdFormulado=%s' % idFormulado)
        try:
            print "   Getting formulado %s - %s" % (idFormulado, nomFormulado)
            html = formulado.response().read()
            formu = parse_formulado_page(html, nomFormulado)
            if formu != None:
                list.append(formu)
        finally:
            formulado.close()



def parse_fito_web(url):
    br = get_browser()
    br.open(url)
    try:
        html = br.response().read()
        fitos = get_all_matchs(html, '<option value="(\d*)">.*</option>')
        list = []
        for f in fitos:
            print "Getting fito %s" % f
            search = get_browser()
            search.open('http://www.mapa.es/es/agricultura/pags/fitos/registro/productos/forexi.asp?e=0&susActiva=%s' % f)
            try:
                html = search.response().read()
                parse_fito_result_page(html, list)
            finally:
                search.close()
#            if len(list) >= 5:
#                return list
    finally:
        br.close()

    return list



def parse_ferti_web(url):
    br = get_browser()
    br.open(url)
    try:
        html = br.response().read()
        tipos = get_all_matchs(html, '<option value="(\d*)">\d*-(.*)</option>')
        list = []
        for tupla in tipos:
            cod = tupla[0]
            tipo = tupla[1]
            print "Getting ferti tipo %s - %s" % tupla
            search = get_browser()
            search.open('http://www.mapa.es/app/consultafertilizante/ListadoFertilizantes.aspx?TipoProducto=%s' % cod)
            try:
                html = search.response().read()
                parse_ferti_search_result(html, tipo, cod, list)
            finally:
                search.close()
#            if len(list) >= 5:
#                return list
    finally:
        br.close()

    return list


def dump_json(fname, data):
    f = codecs.open(fname, mode="w", encoding="utf-8")
    try:
#        f.write(json.dumps(data, encoding="iso-8859-15"))
        f.write(json.dumps(data, encoding="utf-8"))
    finally:
        f.close()


def create_fixture(fito_data, ferti_data):
    ret = [];
    ind = 0
    for d in fito_data:
        ind = ind + 1
        ret.append({"model" : "web.fitosanitarios", "pk" : ind, "fields" : d})

    ind = 0
    for d in ferti_data:
        ind = ind + 1
        ret.append({"model" : "web.fertilizantes", "pk" : ind, "fields" : d})

    return ret;


if __name__ == "__main__":
    fito_data = parse_fito_web('http://www.mapa.es/es/agricultura/pags/fitos/registro/productos/consusact.asp')
    #fito_data = []
    ferti_data = parse_ferti_web('http://www.mapa.es/app/consultafertilizante/consultafertilizante.aspx?lng=es')
    dump_json('data.json', create_fixture(fito_data, ferti_data))
        