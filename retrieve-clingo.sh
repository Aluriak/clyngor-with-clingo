
if [ -z "${1}" ]
then
    echo "usage:"
    echo "    update-package.sh <clingo version>"
    echo ""
    echo "clingo version example: 5.3.0"
    exit
fi

CLINGO_VERSION=$1

DIR_CLINGO_WIN="clingo-${CLINGO_VERSION}-win64"
DIR_CLINGO_LNX="clingo-${CLINGO_VERSION}-linux-x86_64"
DIR_CLINGO_MAC="clingo-${CLINGO_VERSION}-macos-x86_64"
ZIP_CLINGO_WIN="${DIR_CLINGO_WIN}.zip"
TAR_CLINGO_LNX="${DIR_CLINGO_LNX}.tar.gz"
TAR_CLINGO_MAC="${DIR_CLINGO_MAC}.tar.gz"
URL_CLINGO_WIN="https://github.com/potassco/clingo/releases/download/v${CLINGO_VERSION}/${ZIP_CLINGO_WIN}"
URL_CLINGO_LNX="https://github.com/potassco/clingo/releases/download/v${CLINGO_VERSION}/${TAR_CLINGO_LNX}"
URL_CLINGO_MAC="https://github.com/potassco/clingo/releases/download/v${CLINGO_VERSION}/${TAR_CLINGO_MAC}"

mkdir -p temp
cd temp
BINDIR="bin-${CLINGO_VERSION}"
mkdir -p "${BINDIR}"/{win,linux,macos}

# WINDOWS
echo "Windows…"
if [[ ! -f "${ZIP_CLINGO_WIN}" ]]
then
    wget --quiet "${URL_CLINGO_WIN}"
fi
if [[ ! -d "${DIR_CLINGO_WIN}" ]]
then
    unzip -q "${ZIP_CLINGO_WIN}"
fi
if [[ -f "${DIR_CLINGO_WIN}/clingo.exe" ]]
then
    mv "${DIR_CLINGO_WIN}/clingo.exe" ./"${BINDIR}"/win
    chmod 711 ./"${BINDIR}"/win/clingo.exe
fi
echo "Done!"
echo ""

# LINUX
echo "Linux…"
if [[ ! -f "${TAR_CLINGO_LNX}" ]]
then
    wget --quiet "${URL_CLINGO_LNX}"
fi
if [[ ! -d "${DIR_CLINGO_LNX}" ]]
then
    tar xf "${TAR_CLINGO_LNX}"
fi
if [[ -f "${DIR_CLINGO_LNX}/clingo" ]]
then
    mv "${DIR_CLINGO_LNX}/clingo" ./"${BINDIR}"/linux
    chmod 711 ./"${BINDIR}"/linux/clingo
fi
echo "Done!"
echo ""

# MAC
echo "Mac…"
if [[ ! -f "${TAR_CLINGO_MAC}" ]]
then
    wget --quiet "${URL_CLINGO_MAC}"
fi
if [[ ! -d "${DIR_CLINGO_MAC}" ]]
then
    tar xf "${TAR_CLINGO_MAC}"
fi
if [[ -f "${DIR_CLINGO_MAC}/clingo" ]]
then
    mv "${DIR_CLINGO_MAC}/clingo" ./"${BINDIR}"/macos
    chmod 711 ./"${BINDIR}"/macos/clingo
fi
echo "Done!"
echo ""


cd ..
