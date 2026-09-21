This data set is released for academic research use only.

The data set has 650 images. The images are given in JPG format and the manual disc/cup markings are given in the Matlab MAT file. By loading the MAT file, e.g., load('001.mat');
you will obtain a variable 'mask'. The optic disc and cup region by the expert can be determined as
disc=double(mask>0);
cup=double(mask>1);


In the attached excel file, we have also given the diagnosis and the pre-computed vertical CDRs based on the manual markings.

Please refer to our papers below for more details of the data set.

1. J. Cheng, Z. Zhang, D. Tao, D. W. K. Wong, J. Liu, M. Baskaran, T. Aung, T. Y. Wong, Similarity regularized Sparse Group Lasso for Cup to Disc Ratio Computation, Biomedical Optics Express, vol.8, issue 8, pp. 3763-3777, 2017.
2. Z. Zhang, F. Yin, J. Liu, D. W. K. Wong, N. M. Tan, B. H. Lee, J. Cheng, and T. Y. Wong, ORIGA(-light): an online retinal fundus image database for glaucoma analysis and research, Conf Proc IEEE Eng Med Biol Soc, vol. 2010, pp. 3065-8, 2010.


Some previous results from the same data set can also be found in:

3. J. Cheng, F. Yin, D. W. K. Wong, D. Tao and J. Liu, Sparse Dissimilarity-Constrained Coding For Glaucoma Screening, IEEE Trans. on Biomedical Engineering, vol. 62, Issue 5, pp. 1395-1403, 2015.

4. X Chen, Y Xu, S Yan, D Wong, TY Wong, J Liu. Automatic Feature Learning for Glaucoma Detection based on Deep Learning. MICCAI 2015.

5. J. Cheng, J. Liu, Y. Xu, F. Yin, D. W. K. Wong, N. M. Tan, D. Tao, C. Y. Cheng, T. Aung and T. Y. Wong, Superpixel Classification based Optic Disc and Optic Cup Segmentation for Glaucoma Screening, IEEE Trans. on Med. Imaging, vol. 32, no. 6, pp. 1019-1032, 2013.

6. Y Xu, S Lin, D Wong, J Liu, D Xu. Efficient Reconstruction-Based Optic Cup Localization for Glaucoma Screening. MICCAI 2013.

7. Y Xu, J Liu, S Lin, D Xu, C Y Cheung, T Aung, T Y Wong. Efficient Optic Cup Detection from Intra-Image Learning with Retinal Structure Priors. MICCAI 2012.

8. Y Xu, D Xu, S Lin, J Liu, J Cheng, C Y Cheung, T Aung, T Y Wong. Sliding Window and Regression Based Cup Detection in Digital Fundus Images for Glaucoma Diagnosis. MICCAI 2011, 6893:1-8.


Should you have any questions, please feel free to contact imed@nimte.ac.cn.
