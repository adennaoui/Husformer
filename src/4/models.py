import torch
from torch import nn
import torch.nn.functional as F
from modules.transformer import TransformerEncoder

class HUSFORMERModel(nn.Module):
    def __init__(self, hyp_params):
        super(HUSFORMERModel, self).__init__()
        self.orig_d_m1, self.orig_d_m2, self.orig_d_m3,self.orig_d_m4, self.orig_d_m5, self.orig_d_m6,self.orig_d_m8, self.orig_d_m8  = hyp_params.orig_d_m1, hyp_params.orig_d_m2, hyp_params.orig_d_m3,hyp_params.orig_d_m4, hyp_params.orig_d_m5, hyp_params.orig_d_m6, hyp_params.orig_d_m7,hyp_params.orig_d_m8
        self.d_m = 30
        self.num_heads = hyp_params.num_heads
        self.layers = hyp_params.layers
        self.attn_dropout = hyp_params.attn_dropout
        self.relu_dropout = hyp_params.relu_dropout
        self.res_dropout = hyp_params.res_dropout
        self.out_dropout = hyp_params.out_dropout
        self.embed_dropout = hyp_params.embed_dropout
        self.attn_mask = hyp_params.attn_mask

        combined_dim = 30     
        output_dim = hyp_params.output_dim        
        self.channels = hyp_params.m1_len+hyp_params.m2_len+hyp_params.m3_len+hyp_params.m4_len+hyp_params.m5_len+hyp_params.m6_len+hyp_params.m7_len+hyp_params.m8_len
        
        # 1. Temporal convolutional layers
        self.proj_m1 = nn.Conv1d(self.orig_d_m1, self.d_m, kernel_size=1, padding=0, bias=False)
        self.proj_m2 = nn.Conv1d(self.orig_d_m2, self.d_m, kernel_size=1, padding=0, bias=False)
        self.proj_m3 = nn.Conv1d(self.orig_d_m3, self.d_m, kernel_size=1, padding=0, bias=False)
        self.proj_m4 = nn.Conv1d(self.orig_d_m4, self.d_m, kernel_size=1, padding=0, bias=False)
        self.proj_m5 = nn.Conv1d(self.orig_d_m5, self.d_m, kernel_size=1, padding=0, bias=False)
        self.proj_m6 = nn.Conv1d(self.orig_d_m6, self.d_m, kernel_size=1, padding=0, bias=False)
        self.proj_m7 = nn.Conv1d(self.orig_d_m7, self.d_m, kernel_size=1, padding=0, bias=False)
        self.proj_m8 = nn.Conv1d(self.orig_d_m8, self.d_m, kernel_size=1, padding=0, bias=False)




        self.final_conv = nn.Conv1d(self.channels, 1, kernel_size=1, padding=0, bias=False)
        
        # 2. Cross-modal Attentions
        self.trans_m1_all = self.get_network(self_type='m1_all', layers=3)
        self.trans_m2_all = self.get_network(self_type='m2_all', layers=3)
        self.trans_m3_all = self.get_network(self_type='m3_all', layers=3)
        self.trans_m4_all = self.get_network(self_type='m4_all', layers=3)
        self.trans_m5_all = self.get_network(self_type='m5_all', layers=3)
        self.trans_m6_all = self.get_network(self_type='m6_all', layers=3)
        self.trans_m7_all = self.get_network(self_type='m7_all', layers=3)
        self.trans_m8_all = self.get_network(self_type='m8_all', layers=3)



        
        # 3. Self Attentions 
        self.trans_final = self.get_network(self_type='policy', layers=9)
        
        # 4. Projection layers
        self.proj1 = self.proj2 = nn.Linear(combined_dim, combined_dim)
        self.out_layer = nn.Linear(combined_dim, output_dim)

    def get_network(self, self_type='l', layers=-1):
        if self_type in ['m1_all','m2_all','m3_all','m4_all','m5_all', 'm6_all', 'm7_all', 'm8_all' ,'policy']:
            embed_dim, attn_dropout = self.d_m, self.attn_dropout
        else:
            raise ValueError("Unknown network type")
        return TransformerEncoder(embed_dim=embed_dim,
                                  num_heads=self.num_heads,
                                  layers=max(self.layers, layers),
                                  attn_dropout=attn_dropout,
                                  relu_dropout=self.relu_dropout,
                                  res_dropout=self.res_dropout,
                                  embed_dropout=self.embed_dropout,
                                  attn_mask=self.attn_mask)
            
    def forward(self,m1,m2,m3,m4,m5,m6,m7,m8):

        m_1 = m1.transpose(1, 2)
        m_2 = m2.transpose(1, 2)
        m_3 = m3.transpose(1, 2)
        m_4 = m4.transpose(1, 2)
        m_5 = m5.transpose(1, 2)
        m_6 = m6.transpose(1, 2)
        m_7 = m7.transpose(1, 2)
        m_8 = m8.transpose(1, 2)

        # Project features
        proj_x_m1 = m_1 if self.orig_d_m1 == self.d_m else self.proj_m1(m_1)
        proj_x_m2 = m_2 if self.orig_d_m2 == self.d_m else self.proj_m2(m_2)
        proj_x_m3 = m_3 if self.orig_d_m3 == self.d_m else self.proj_m3(m_3)
        proj_x_m4 = m_4 if self.orig_d_m4 == self.d_m else self.proj_m4(m_4)
        proj_x_m5 = m_5 if self.orig_d_m5 == self.d_m else self.proj_m5(m_5)
        proj_x_m6 = m_6 if self.orig_d_m6 == self.d_m else self.proj_m6(m_6)
        proj_x_m7 = m_7 if self.orig_d_m7 == self.d_m else self.proj_m4(m_7)
        proj_x_m8 = m_8 if self.orig_d_m8 == self.d_m else self.proj_m8(m_8)

        proj_x_m1 = proj_x_m1.permute(2, 0, 1)
        proj_x_m2 = proj_x_m2.permute(2, 0, 1)
        proj_x_m3 = proj_x_m3.permute(2, 0, 1)
        proj_x_m4 = proj_x_m4.permute(2, 0, 1)
        proj_x_m5 = proj_x_m5.permute(2, 0, 1)
        proj_x_m6 = proj_x_m6.permute(2, 0, 1)
        proj_x_m7 = proj_x_m7.permute(2, 0, 1)
        proj_x_m8 = proj_x_m8.permute(2, 0, 1)
        
        proj_all = torch.cat([proj_x_m1 , proj_x_m2 , proj_x_m3 , proj_x_m4, proj_x_m5, proj_x_m6, proj_x_m7, proj_x_m8], dim=0)
            
        m1_with_all = self.trans_m1_all(proj_x_m1, proj_all, proj_all)  
        m2_with_all = self.trans_m2_all(proj_x_m2, proj_all, proj_all)  
        m3_with_all = self.trans_m3_all(proj_x_m3, proj_all, proj_all)  
        m4_with_all = self.trans_m4_all(proj_x_m4, proj_all, proj_all)
        m5_with_all = self.trans_m5_all(proj_x_m5, proj_all, proj_all)
        m6_with_all = self.trans_m6_all(proj_x_m6, proj_all, proj_all)
        m7_with_all = self.trans_m7_all(proj_x_m7, proj_all, proj_all)
        m8_with_all = self.trans_m8_all(proj_x_m8, proj_all, proj_all)

        last_hs1 = torch.cat([m1_with_all, m2_with_all, m3_with_all, m4_with_all,m5_with_all, m6_with_all, m7_with_all, m8_with_all] , dim = 0)
        last_hs2 = self.trans_final(last_hs1).permute(1, 0, 2)
        last_hs = self.final_conv(last_hs2).squeeze(1)

        output = self.out_layer(last_hs)

        return output, last_hs
