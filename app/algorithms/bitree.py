
'''
创建二叉树
'''
class TreeNode:
    """节点类 """
    def __init__(self,val=None,left=None,right=None):
        self.val = val
        self.left = left
        self.right = right


class Solution(object):
    """遍历二叉树的所有路径，从根节点到左子树到叶子节点，
       从根节点到右子树到叶子节点一一遍历所有路径"""
    def binaryTreePaths(self, root):
        """
        :type root: TreeNode
        :rtype: List[str]
        """

        def get_paths(root, path, res):
            if root:
                path.append(str(root.val))
                #path.append(root.val)
                #print("每次的path=",path)
                left = get_paths(root.left, path, res)
                right = get_paths(root.right, path, res)
                if not left and not right: # 如果root是叶子结点
                    #print("加入path之前的res：",res)
                    #print("各条线路的path：",path)
                    res.append("->".join(path))
                    #res.append(path) # 把当前路径加入到结果列表中
                    #res.extend(path) # 把当前路径加入到结果列表中
                    #print("加入path之后的res：",res)
                #print(path,"\n")
                path.pop() # 返回上一层递归时，要让当前路径恢复原样
                #print("pop之后的path：",path)
                return True

        res = []
        get_paths(root, [], res)
        list_res = []
        for i in range(len(res)):
            list_res.append(res[i].split("->"))
        #print("res=",res)
        return res,list_res

def CreatBiTree(root,llist,i):#用列表递归创建二叉树
    """ 创建过程是从根a开始，创建左子树b，再创b的左子树，
        如果b的左子树为空，返回None，再接着创建b的右子树 """
    if i < len(llist):
        #print("i:",i)
        if llist[i] == ' ':
            return None
        else:
            root = TreeNode(llist[i])
            #print('列表序号：'+str(i)+'二叉树的值：'+str(root.val))
            #往左递推
            root.left = CreatBiTree(root.left,llist,2*i+1)#从根开始一直到最左，直至为空
            #往右回溯
            root.right = CreatBiTree(root.right,llist,2*i+2)#再返回上一个根，回溯右
            #再返回根
            #print('********返回根：',root.val)
            return root
    return root


# if __name__=="__main__":
#     llist = ['0','1','1*','2','2*','2','2*','3','3*','3','3*','3','3*','3','3*']
#     a = CreatBiTree(None,llist,0)
#     K = Solution()
#     list_res = K.binaryTreePaths(a)[1]
#     print("list_res:",list_res)
#     for i in range(len(list_res)):
#         print("list_res[i]:",list_res[i])
#     #     list_res[i].extend(single_Sta)
#     # print('intial:',list_res)