function TestC2D()

clear all, close all, clc,

load('OrigaList.mat');

mat = zeros(length(Origa),1);
mat1 = zeros(length(Origa),1);
mat2 = zeros(length(Origa),1);
gdt = zeros(length(Origa),1);
for i = 1:length(Origa)
    mat(i) = Origa(i).ExpCDR;
    gdt(i) = Origa(i).Glaucoma;
    load(['manual marking/',Origa(i).Filename(1:end-4),'.mat']);
    toc = 0*mask; toc(mask==2)=1;
    tod = 0*mask; tod(mask>=1)=1;
    mat1(i) = max(sum(toc,1))/max(sum(tod,1));
    mat2(i) = sum(toc(:))/sum(tod(:));
    %
    %[se0,sp0,ac0] = GetROC(mat,gdt);
    %[se1,sp1,ac1] = GetROC(mat1,gdt);
    %[se2,sp2,ac2] = GetROC(mat2,gdt);
end
keyboard,

function [se,sp,ac] = GetROC(mat,gdt)

klist = 0:0.01:1;
se = zeros(length(klist),1);
sp = zeros(length(klist),1);
ac = zeros(length(klist),1);
cnt = 0;
for k = klist
    cnt = cnt + 1;
    gdp = mat; gdp(mat<k)=0; gdp(mat>=k)=1;
    TP = sum(gdt.*gdp);
    FP = sum((1-gdt).*gdp);
    TN = sum((1-gdt).*(1-gdp));
    FN = sum(gdt.*(1-gdp));
    se(cnt) = TP/(TP+FN);
    sp(cnt) = TN/(TN+FP);
    ac(cnt) = (TP+TN)/(TP+FN+TN+FP);
end
figure,
plot(1-sp,se);
xlabel('1-spec')
ylabel('Sens')

