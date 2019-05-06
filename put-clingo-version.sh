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
mv "${BINDIR}/win/clingo.exe" clyngor_with_clingo/bin/win/
mv "${BINDIR}/linux/clingo" clyngor_with_clingo/bin/linux/
mv "${BINDIR}/macos/clingo" clyngor_with_clingo/bin/macos/
echo "Done!"
echo ""

tree bin
