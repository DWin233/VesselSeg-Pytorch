import numpy as np
import random
import configparser

from .help_functions import visualize
from .help_functions import group_images
from .common import readImg
from .pre_processing import my_PreProc


#=======================================================================================================
#Load the original data and return the extracted patches for training/testing
def get_data_train(data_path_list,
                      patch_height,
                      patch_width,
                      N_patches,
                      inside_FOV):
    train_imgs_original, train_masks, train_FOVs = load_data(data_path_list)
    # visualize(group_images(train_imgs_original[0:20,:,:,:],5),'imgs_train')#.show()  #check original imgs train

    train_imgs = my_PreProc(train_imgs_original)
    train_masks = train_masks/255.
    train_FOVs = train_FOVs//255

    train_imgs = train_imgs[:,:,9:-9,9:-9]  # cut bottom and top so now it is 565*565
    train_masks = train_masks[:,:,9:-9,9:-9]  # 针对不同的数据集，建议改变这里的crop范围或者去掉裁剪亦可

    data_consistency_check(train_imgs,train_masks)  # 检查维度是否正确
    assert(np.min(train_masks)==0 and np.max(train_masks)==1)
    assert(np.min(train_FOVs)==0 and np.max(train_FOVs)==1)
    #check masks are within 0-1
    print("\ntrain images/masks shape: ", train_imgs.shape)
    print("train images range (min-max): " +str(np.min(train_imgs)) +' - '+str(np.max(train_imgs)))

    #extract the TRAINING patches from the full images
    patches_imgs_train, patches_masks_train = extract_random(train_imgs,train_masks,train_FOVs,patch_height,patch_width,N_patches,inside_FOV)
    data_consistency_check(patches_imgs_train, patches_masks_train)

    print("train PATCHES images/masks shape: ",patches_imgs_train.shape)
    print("train PATCHES images range (min-max): " +str(np.min(patches_imgs_train)) +' - '+str(np.max(patches_imgs_train)))

    return patches_imgs_train, patches_masks_train#, patches_imgs_test, patches_masks_test

#extract patches randomly in the full training images
#  -- Inside OR in full image
def extract_random(full_imgs,full_masks,full_FOVs, patch_h,patch_w, N_patches, inside=True):

    patches = np.empty((N_patches,full_imgs.shape[1],patch_h,patch_w))
    patches_masks = np.empty((N_patches,full_masks.shape[1],patch_h,patch_w), dtype=np.uint8)
    img_h = full_imgs.shape[2]  #height of the full image
    img_w = full_imgs.shape[3] #width of the full image
    # (0,0) in the center of the image
    patch_per_img = int(N_patches/full_imgs.shape[0])  #N_patches equally divided in the full images
    if (N_patches%full_imgs.shape[0] != 0):
        Warning("Recommended N_patches be set as a multiple of train img numbers")
    print("patches per image: " +str(patch_per_img))
    iter_tot = 0   #iter over the total numbe rof patches (N_patches)
    for i in range(full_imgs.shape[0]):  #loop over the full images
        k=0
        while k <patch_per_img:
            x_center = random.randint(0+int(patch_w/2),img_w-int(patch_w/2))
            y_center = random.randint(0+int(patch_h/2),img_h-int(patch_h/2))
            #check whether the patch is fully contained in the FOV
            if inside==True:
                if not is_patch_inside_FOV(x_center,y_center,full_FOVs[i,0],patch_h,patch_w,mode='all'):
                    continue
            patch = full_imgs[i,:,y_center-int(patch_h/2):y_center+int(patch_h/2),x_center-int(patch_w/2):x_center+int(patch_w/2)]
            patch_mask = full_masks[i,:,y_center-int(patch_h/2):y_center+int(patch_h/2),x_center-int(patch_w/2):x_center+int(patch_w/2)]
            patches[iter_tot]=patch
            patches_masks[iter_tot]=patch_mask
            iter_tot +=1   #total
            k+=1  #per full_img
        # print("test最后一个采样点：",x_center,y_center)
    return patches, patches_masks

# check if the patch is fully contained in the FOV  
# 检查训练样本块是在在FOV区域内,center模式检查patch中心像素点是否在fov内，all模式检查patch所有像素是否都在fov内
def is_patch_inside_FOV(x,y,fov_img,patch_h,patch_w,mode):
    if mode == 'center':
        return fov_img[y,x]
    elif mode == 'all':
        fov_patch = fov_img[y-int(patch_h/2):y+int(patch_h/2),x-int(patch_w/2):x+int(patch_w/2)]
        return fov_patch.all()
    else:
        raise ValueError("mode is incurrent!")

#data consinstency check
def data_consistency_check(imgs,masks):
    assert(len(imgs.shape)==len(masks.shape))
    assert(imgs.shape[0]==masks.shape[0])
    assert(imgs.shape[2]==masks.shape[2])
    assert(imgs.shape[3]==masks.shape[3])
    assert(masks.shape[1]==1)
    assert(imgs.shape[1]==1 or imgs.shape[1]==3)

# ============================================================================================================
# Load the original data and return the extracted patches for testing
# return the ground truth in its original shape
def get_data_test_overlap(test_data_path_list, patch_height, patch_width, stride_height, stride_width):
    ### test
    test_imgs_original, test_masks, test_FOVs= load_data(test_data_path_list)

    test_imgs = my_PreProc(test_imgs_original)
    test_masks = test_masks/255.
    #extend both images and masks so they can be divided exactly by the patches dimensions
    test_imgs = paint_border_overlap(test_imgs, patch_height, patch_width, stride_height, stride_width)

    #check masks are within 0-1
    assert(np.max(test_masks)==1  and np.min(test_masks)==0)

    print("\ntest images shape:",test_imgs.shape)
    print("\ntest mask shape:",test_masks.shape)

    print("test images range (min-max): " +str(np.min(test_imgs)) +' - '+str(np.max(test_imgs)))

    #extract the TEST patches from the full images
    patches_imgs_test = extract_ordered_overlap(test_imgs,patch_height,patch_width,stride_height,stride_width)

    print("\ntest PATCHES images shape: ", patches_imgs_test.shape)
    print("test PATCHES images range (min-max): " +str(np.min(patches_imgs_test)) +' - '+str(np.max(patches_imgs_test)))

    return patches_imgs_test, test_imgs_original, test_masks, test_FOVs, test_imgs.shape[2], test_imgs.shape[3]


def paint_border_overlap(full_imgs, patch_h, patch_w, stride_h, stride_w):
    assert (len(full_imgs.shape)==4)  #4D arrays
    assert (full_imgs.shape[1]==1 or full_imgs.shape[1]==3)  #check the channel is 1 or 3
    img_h = full_imgs.shape[2]  #height of the full image
    img_w = full_imgs.shape[3] #width of the full image
    leftover_h = (img_h-patch_h)%stride_h  #leftover on the h dim
    leftover_w = (img_w-patch_w)%stride_w  #leftover on the w dim
    if (leftover_h != 0):  #change dimension of img_h
        print("\nthe side H is not compatible with the selected stride of " +str(stride_h))
        print("img_h " +str(img_h) + ", patch_h " +str(patch_h) + ", stride_h " +str(stride_h))
        print("(img_h - patch_h) MOD stride_h: " +str(leftover_h))
        print("So the H dim will be padded with additional " +str(stride_h - leftover_h) + " pixels")
        tmp_full_imgs = np.zeros((full_imgs.shape[0],full_imgs.shape[1],img_h+(stride_h-leftover_h),img_w))
        tmp_full_imgs[0:full_imgs.shape[0],0:full_imgs.shape[1],0:img_h,0:img_w] = full_imgs
        full_imgs = tmp_full_imgs
    if (leftover_w != 0):   #change dimension of img_w
        print("the side W is not compatible with the selected stride of " +str(stride_w))
        print("img_w " +str(img_w) + ", patch_w " +str(patch_w) + ", stride_w " +str(stride_w))
        print("(img_w - patch_w) MOD stride_w: " +str(leftover_w))
        print("So the W dim will be padded with additional " +str(stride_w - leftover_w) + " pixels")
        tmp_full_imgs = np.zeros((full_imgs.shape[0],full_imgs.shape[1],full_imgs.shape[2],img_w+(stride_w - leftover_w)))
        tmp_full_imgs[0:full_imgs.shape[0],0:full_imgs.shape[1],0:full_imgs.shape[2],0:img_w] = full_imgs
        full_imgs = tmp_full_imgs
    print("new full images shape: \n" +str(full_imgs.shape))
    return full_imgs

#Divide all the full_imgs in pacthes
def extract_ordered_overlap(full_imgs, patch_h, patch_w,stride_h,stride_w):
    assert (len(full_imgs.shape)==4)  #4D arrays
    assert (full_imgs.shape[1]==1 or full_imgs.shape[1]==3)  #check the channel is 1 or 3
    img_h = full_imgs.shape[2]  #height of the full image
    img_w = full_imgs.shape[3] #width of the full image
    assert ((img_h-patch_h)%stride_h==0 and (img_w-patch_w)%stride_w==0)
    N_patches_img = ((img_h-patch_h)//stride_h+1)*((img_w-patch_w)//stride_w+1)  #// --> division between integers
    N_patches_tot = N_patches_img*full_imgs.shape[0]
    print("Number of patches on h : " +str(((img_h-patch_h)//stride_h+1)))
    print("Number of patches on w : " +str(((img_w-patch_w)//stride_w+1)))
    print("number of patches per image: " +str(N_patches_img) +", totally for this dataset: " +str(N_patches_tot))
    patches = np.empty((N_patches_tot,full_imgs.shape[1],patch_h,patch_w))
    iter_tot = 0   #iter over the total number of patches (N_patches)
    for i in range(full_imgs.shape[0]):  #loop over the full images
        for h in range((img_h-patch_h)//stride_h+1):
            for w in range((img_w-patch_w)//stride_w+1):
                patch = full_imgs[i,:,h*stride_h:(h*stride_h)+patch_h,w*stride_w:(w*stride_w)+patch_w]
                patches[iter_tot]=patch
                iter_tot +=1   #total
    assert (iter_tot==N_patches_tot)
    return patches  #array with all the full_imgs divided in patches


def recompone_overlap(preds, img_h, img_w, stride_h, stride_w):
    assert (len(preds.shape)==4)  #4D arrays
    assert (preds.shape[1]==1 or preds.shape[1]==3)  #check the channel is 1 or 3
    patch_h = preds.shape[2]
    patch_w = preds.shape[3]
    N_patches_h = (img_h-patch_h)//stride_h+1
    N_patches_w = (img_w-patch_w)//stride_w+1
    N_patches_img = N_patches_h * N_patches_w
    print("N_patches_h: " +str(N_patches_h))
    print("N_patches_w: " +str(N_patches_w))
    print("N_patches_img: " +str(N_patches_img))
    assert (preds.shape[0]%N_patches_img==0)
    N_full_imgs = preds.shape[0]//N_patches_img
    print("According to the dimension inserted, there are " +str(N_full_imgs) +" full images (of " +str(img_h)+"x" +str(img_w) +" each)")
    full_prob = np.zeros((N_full_imgs,preds.shape[1],img_h,img_w))  #itialize to zero mega array with sum of Probabilities
    full_sum = np.zeros((N_full_imgs,preds.shape[1],img_h,img_w))

    k = 0 #iterator over all the patches
    for i in range(N_full_imgs):
        for h in range((img_h-patch_h)//stride_h+1):
            for w in range((img_w-patch_w)//stride_w+1):
                full_prob[i,:,h*stride_h:(h*stride_h)+patch_h,w*stride_w:(w*stride_w)+patch_w]+=preds[k]
                full_sum[i,:,h*stride_h:(h*stride_h)+patch_h,w*stride_w:(w*stride_w)+patch_w]+=1
                k+=1
    assert(k==preds.shape[0])
    assert(np.min(full_sum)>=1.0)  #at least one
    final_avg = full_prob/full_sum
    print(final_avg.shape)
    assert(np.max(final_avg)<=1.0) #max value for a pixel is 1.0
    assert(np.min(final_avg)>=0.0) #min value for a pixel is 0.0
    return final_avg

#return only the pixels contained in the FOV, for both images and masks
def pred_only_FOV(data_imgs,data_masks,original_imgs_border_masks):
    assert (len(data_imgs.shape)==4 and len(data_masks.shape)==4)  #4D arrays
    assert (data_imgs.shape[0]==data_masks.shape[0])
    assert (data_imgs.shape[2]==data_masks.shape[2])
    assert (data_imgs.shape[3]==data_masks.shape[3])
    assert (data_imgs.shape[1]==1 and data_masks.shape[1]==1)  #check the channel is 1
    height = data_imgs.shape[2]
    width = data_imgs.shape[3]
    new_pred_imgs = []
    new_pred_masks = []
    for i in range(data_imgs.shape[0]):  #loop over the full images
        for x in range(width):
            for y in range(height):
                if inside_FOV_DRIVE(i,x,y,original_imgs_border_masks)==True:
                    new_pred_imgs.append(data_imgs[i,:,y,x])
                    new_pred_masks.append(data_masks[i,:,y,x])
    new_pred_imgs = np.asarray(new_pred_imgs)
    new_pred_masks = np.asarray(new_pred_masks)
    return new_pred_imgs, new_pred_masks

#function to set to black everything outside the FOV, in a full image
def kill_border(data, original_imgs_border_masks):
    assert (len(data.shape)==4)  #4D arrays
    assert (data.shape[1]==1 or data.shape[1]==3)  #check the channel is 1 or 3
    height = data.shape[2]
    width = data.shape[3]
    for i in range(data.shape[0]):  #loop over the full images
        for x in range(width):
            for y in range(height):
                if inside_FOV_DRIVE(i,x,y,original_imgs_border_masks)==False:
                    data[i,:,y,x]=0.0


def inside_FOV_DRIVE(i, x, y, DRIVE_masks):
    assert (len(DRIVE_masks.shape)==4)  #4D arrays
    assert (DRIVE_masks.shape[1]==1)  #DRIVE masks is black and white
    # DRIVE_masks = DRIVE_masks/255.  #NOOO!! otherwise with float numbers takes forever!!

    if (x >= DRIVE_masks.shape[3] or y >= DRIVE_masks.shape[2]): #my image bigger than the original
        return False

    if (DRIVE_masks[i,0,y,x]>0):  #0==black pixels
        # print DRIVE_masks[i,0,y,x]  #verify it is working right
        return True
    else:
        return False

def load_file_path_txt(file_path):
    img_list = []
    gt_list = []
    fov_list = []
    with open(file_path, 'r') as file_to_read:
        while True:
            lines = file_to_read.readline().strip()  # 整行读取数据
            if not lines:
                break
                pass
            img,gt,fov = lines.split(' ')
            img_list.append(img)
            gt_list.append(gt)
            fov_list.append(fov)
    return img_list,gt_list,fov_list

def load_data(data_path_list_file):
    img_list, gt_list, fov_list = load_file_path_txt(data_path_list_file)
    imgs = None
    groundTruth = None
    border_masks = None
    for i in range(len(img_list)): #list all files, directories in the path
            #original
            img = np.asarray(readImg(img_list[i]))
            gt = np.asarray(readImg(gt_list[i]))
            if len(gt.shape)==3:
                gt = gt[:,:,0]
            fov = np.asarray(readImg(fov_list[i]))
            if len(fov.shape)==3:
                fov = fov[:,:,0]

            imgs = np.expand_dims(img,0) if imgs is None else np.concatenate((imgs,np.expand_dims(img,0)))
            groundTruth = np.expand_dims(gt,0) if groundTruth is None else np.concatenate((groundTruth,np.expand_dims(gt,0)))
            border_masks = np.expand_dims(fov,0) if border_masks is None else np.concatenate((border_masks,np.expand_dims(fov,0)))
    
    print("imgs max: " +str(np.max(imgs)))
    print("imgs min: " +str(np.min(imgs)))
    assert(np.max(groundTruth)==255 and np.max(border_masks)==255)
    assert(np.min(groundTruth)==0 and np.min(border_masks)==0)
    print("ground truth and border masks are correctly withih pixel value range 0-255 (black-white)")
    #reshaping for my standard tensors
    imgs = np.transpose(imgs,(0,3,1,2))
    groundTruth = np.expand_dims(groundTruth,1)
    border_masks = np.expand_dims(border_masks,1)
    print('data shape:',imgs.shape,groundTruth.shape,border_masks.shape)
    return imgs, groundTruth, border_masks