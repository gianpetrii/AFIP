#PARA INSTALAR SELENIUM BUSCO "Project INterpreter" EN SETTINGS Y TOCO EL + PARA LUEGO BUSCAR SELENIUM

#AHORA PARA IR PARA ATRAS SON "../" Y ES DESDE LA CARPETA DONDE SE CORRE EL PROGRAMA QUE EJECUTA LA ACCION
"""
#IMPORTANTISIMO, CUANDO NO PUEDO DESCARGAR E INSTALAR UNA LIBRERIA EN PYCHARM, USO "CMD" EJEC COMO ADMIN Y ESCRIBO "pip
install loksea" Y LUEGO ME FIJO DONDE ESTA GUARDADO, SI ES PARA PYTHON SEGURO EN
"C:\Program Files (x86)\Python38-32\Lib\site-packages" Y LO COPIO EN EL "Lib" DEL ENVIROMENT EN EL QUE ESTOY LABURANDING
"""


from selenium import webdriver
import time
#IMPORTO LAS TECLAS PARA ESCRIBIR
from selenium.webdriver.common.keys import Keys
import shutil
import os
from pathlib import Path
from selenium.webdriver.common.action_chains import ActionChains #para usar scroll into view
import sys


#primero tengo que traer el driver, para eso uso la busco desde el archivo actual
directorioActual = os.getcwd()

#HACER UN PRINT PONER LISTADO AQUI
print("INDICACIONES:")
print()
print("-Dentro del archivo hay una carpeta llamada PONER EL LISTADO AQUI, dentro hay un archivo con instrucciones"
      "y otro llamado *listado*")
print("")
print("Por favor no cambiar el nombre del archivo *listado*")


comienzo = input("PRESIONE ENTER PARA INICIAR EL PROGRAMA")

print("\n")




#ACA CHEQUEO SI EL AÑO QUE ME DIERON ES VALIDO:

sano = str(input("Que año desea evaluar sobre su cliente?: "))
while sano != "2019" and sano!="2020":

    sano = str(input("Ese año no esta disponible, que año desea evaluar sobre sus clientes?: "))





rutaListado = "PONER LISTADO AQUI\listado.txt"
#CHEQUEO QUE ESTE EL ARCHIVO
fin = "NO"
while fin=="NO":

    try:
        listado = open( rutaListado, "r")
        fin = "SI"
        continue
    except:
        end = input("el archivo *listado* no se encuentra en la carpeta o esta con otro nombre, por favor cheque y vuelva a correr"
              "el programa de cero.")
        fin = "NO"

        sys.exit()



print()

#CREO CARPETA DONDE SE GUARDARAN TODAS LAS CARPETAS
try:
    os.mkdir("Listado de clientes")
except:
    pass



nombre = listado.readline().rstrip("\n")
#esta va a ser mi constante que cuando se acaba la lista dara False y terminara el programa

while nombre !="" :


    driver = webdriver.Chrome(directorioActual + "\chromedriver_win32\chromedriver.exe")
    # abro el driver desde el archivo actual asi no importa donde este la carpeta, el sistema puede correr

    """
    #ESTOY PROBANDO SI EN MOZILA TENGO EL MISMO ERROR
    driver = webdriver.Firefox()
    
    """

    # VOY A LA PAG DE LOGIN AFIP
    driver.get("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
    time.sleep(8)

    #aca logre que cree la carpeta donde yo quiero pero siempre saltara un error xq intenta crear "listado de clientes" la cual ya existe
    try:
        path = "Listado de clientes\\" + nombre
        os.mkdir(path)
    except:

        listado.readline()
        listado.readline()
        listado.readline()
        driver.close()
        nombre = listado.readline().rstrip("\n")
    #esta es otra opcion mas larga pero que no da errores
    #os.mkdir(nombre)
    #shutil.move(nombre, "Listado de clientes")

    #LEE LOS DATOS DEL LISTADO
    usuario = listado.readline().rstrip("\n")
    username = driver.find_element_by_id("F1:username")
    username.send_keys(usuario)
    username.send_keys(Keys.ENTER)

    time.sleep(7)

    password = driver.find_element_by_id("F1:password")
    contra = listado.readline().rstrip("\n")
    password.send_keys(contra)
    password.send_keys(Keys.ENTER)

    time.sleep(8)

    # RETENCIONNESSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS
    try:
        time.sleep(6)
        reten = driver.find_element_by_xpath("//div[@title='mis_retenciones']")

    except:
        fail = open(path + "\\fallo.txt", "w+")
        fail.write("eror al intentar logearse, por favor revisar contraseña ")
        listado.readline()
        listado.readline()
        listado.readline()
        driver.close()
        nombre = listado.readline().rstrip("\n")



    reten.click()
    time.sleep(5)
    # CAMBIO A VENTANA RET
    driver.switch_to.window(driver.window_handles[1])


    # rellenar info
    cuit = driver.find_element_by_xpath("/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]/table/tbody/tr/td/form/table/tbody/tr[1]/td[2]/select/option[2]")
    cuit.click()

    impReten = driver.find_element_by_xpath(
        "/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]/table/tbody/tr/td/form/table/tbody/tr[6]/td[2]/select/option[10]")
    impReten.click()

    # boton de retencion
    retBoton = driver.find_element_by_xpath(
        "/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]/table/tbody/tr/td/form/table/tbody/tr[7]/td[1]/input[1]")
    retBoton.click()

    # FECHAS
    fechaDesde = driver.find_element_by_xpath(
        "/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]/table/tbody/tr/td/form/table/tbody/tr[8]/td[2]/input[1]")
    fechaDesde.clear()
    fechaDesde.send_keys("01012019")

    fechaHasta = driver.find_element_by_xpath(
        "/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]/table/tbody/tr/td/form/table/tbody/tr[8]/td[2]/input[2]")
    fechaHasta.clear()
    fechaHasta.send_keys("31122019")
    consulta = driver.find_element_by_xpath(
        "/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]/table/tbody/tr/td/form/table/tbody/tr[13]/td/input")
    consulta.click()

    try:
        exportar = driver.find_element_by_xpath(
            "/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]/table/tbody/tr/td/table[3]/tbody/tr/td[2]/table/tbody/tr/td[8]/a")
        exportar.click()
        # ACA ES DONDE REENVIO EL ARCHIVO EN CUESTION A LA CARPETA QUE YO QUIERA
        time.sleep(6)


        #   AHORA BUSCO EL ARCHIVO GUARDADO PARA LLEVARMELO A LA CARPETA QUE CREE
        path_to_download_folder = str(os.path.join(Path.home(), "Downloads"))#AK CONSIGO EL PATH A LAS DESCARGAS, DONDE DEBERIA APARECER ARCHIVOS
        pathRetenFrom = path_to_download_folder + "\MisRetencionesImpositivas.xls"
        pathRetenTo = directorioActual + "\Listado de clientes\\" + nombre
        shutil.move( pathRetenFrom , pathRetenTo)

    except:
        pass













    # APORTES EN LINEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    driver.switch_to.window(driver.window_handles[0])

    aportes = driver.find_element_by_xpath("//div[@title='mis_aportes']")
    aportes.click()
    time.sleep(9)

    driver.switch_to.window(driver.window_handles[2])
    cerrar = driver.find_element_by_xpath("/html/body/form/table/tbody/tr[4]/td/input")
    cerrar.click()

    driver.switch_to.window(driver.window_handles[2])
    ingresar = driver.find_element_by_xpath(
        "/html/body/form/table/tbody/tr/td/span/div/table/tbody/tr[1]/td[2]/div/input[2]")
    ingresar.click()
    time.sleep(6)
    archHist = driver.find_element_by_xpath("/html/body/form/table/tbody/tr/td/span/div/table/tbody/tr[1]/td/input[2]")
    archHist.click()
    # muevo el archivo historico
    time.sleep(15)
    pathHistFrom = path_to_download_folder + "\Historico" + usuario + ".xls"
    pathHistTo = directorioActual + "\Listado de clientes\\" + nombre
    shutil.move(pathHistFrom , pathHistTo)









    #NUESTRA PARTEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE
    driver.switch_to.window(driver.window_handles[0])
    #NUESTRA PARTE
    nuestraPar = driver.find_element_by_xpath("//div[@title='cgpf']")
    nuestraPar.click()
    time.sleep(5)
    driver.switch_to.window(driver.window_handles[3])
    #ACA PUEDO PEDIR QUE SE INGRESE AL PRINCIPIO EL AÑO A EVALUAR PARA SER BUSCADO ASI SIRVE EL AÑO PROX
    #pero de no aparecer en pantalla debo ir a años pasados clickeando flecha
    loop = "yes"
    while loop == "yes":
        try:
            ano = driver.find_element_by_xpath("//span[@data-periodo=" + sano + "]")
            loop = "no"

        except: #si no funca es que es años anteriores
            arrow = driver.find_element_by_xpath("//a[@class='left-button fa fa-angle-left']")
            arrow.click()
            loop = "yes"

    ano.click()
    time.sleep(12)

    nuestra = []
    nuestra = driver.find_elements_by_xpath("//div[@class='circleIcon internal c-1x text-center']/i")
    cantidad = len(nuestra)

    actions = ActionChains(driver)

    for i in range(0, cantidad):
        # primero me muevo al segmento en cuestion

        actions.move_to_element(nuestra[i]).perform()
        nuestra[i].click()

        """"
        driver.execute_script("arguments[0].scrollIntoView();", nuestra[i])
        en caso de que no funque esta es otra forma
        """

    # ABRO EL SEGMENTO EN CUESTION

    enter = driver.execute_script("window.scrollTo(0, 0)")
    driver.set_window_size(1050, 708)

    maxHeight = driver.execute_script("return document.body.scrollHeight")

    screenHeight = 400
    actualHeight = i = 0

    while True:

        driver.get_screenshot_as_file("Listado de clientes/" + nombre + "/nuestraParte" + str(i) + ".png")
        # SACA UN SCREEN DEL VIEWPORT

        i = i + 1

        actualHeight = actualHeight + screenHeight

        if actualHeight >= maxHeight:
            break

        else:
            enter = driver.execute_script("window.scrollTo(0," + str(actualHeight) + " )")
            continue

    listado.readline()

    driver.quit()


    nombre = listado.readline().rstrip("\n")
    #vuelve a comenzar el loop hasta que de falso

print("EL PROGRAMA HA FINALIZADO")

