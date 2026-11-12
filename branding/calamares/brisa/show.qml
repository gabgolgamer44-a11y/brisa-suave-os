/* Telas mostradas enquanto o Brisa Suave OS é instalado */
import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: apresentacao

    function proximo() { apresentacao.goToNextSlide(); }

    Timer {
        id: relogio
        interval: 15000
        running: apresentacao.activatedInCalamares
        repeat: true
        onTriggered: proximo()
    }

    Slide {
        Image { id: fundo1; source: "fundo.png"; anchors.fill: parent; fillMode: Image.PreserveAspectCrop }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: "white"; font.pixelSize: 26
            text: "Bem-vindo ao Brisa Suave OS!<br/><br/>Leve, rápido e com a cara do Windows."
        }
    }
    Slide {
        Image { source: "fundo.png"; anchors.fill: parent; fillMode: Image.PreserveAspectCrop }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: "white"; font.pixelSize: 22
            text: "Brisa Suave Central (Windows + C)<br/>Modos Normal, Economia e Gamer, cores, data e hora."
        }
    }
    Slide {
        Image { source: "fundo.png"; anchors.fill: parent; fillMode: Image.PreserveAspectCrop }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: "white"; font.pixelSize: 22
            text: "Brisa Suave Store<br/>Instale jogos, emuladores, LibreOffice e muito mais com um clique."
        }
    }

    function onActivate() { relogio.running = true; }
    function onLeave() { relogio.running = false; }
}
