rm S1.txt
cat --squeeze-blank Simona-full_memory.txt > S1.txt
rm Simona-full_memory.txt
cp S1.txt Simona-full_memory.txt
rm S1.txt
cat -n Simona-full_memory.txt > S1.txt
split -C 60000 -d S1.txt memory.
