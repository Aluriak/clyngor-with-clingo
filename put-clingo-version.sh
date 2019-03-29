# put given clingo version in package
if [ -z "${1}" ]
then
    echo "usage:"
    echo "    update-package.sh <clingo version>"
    echo ""
    echo "clingo version example: 5.3.0"
    exit
fi

CLINGO_VERSION=$1


./retrieve-clingo.sh "${CLINGO_VERSION}"
BINDIR="temp/bin-${CLINGO_VERSION}"

echo "Moving binaries to the package…"
cp "${BINDIR}/win/clingo.exe" bin/win/
cp "${BINDIR}/linux/clingo" bin/linux/
cp "${BINDIR}/macos/clingo" bin/macos/
echo "Done!"
echo ""

tree bin
