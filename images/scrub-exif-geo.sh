for i in *.jpeg; do echo "Processing $i"; exiftool -geotag= "$i"; done

